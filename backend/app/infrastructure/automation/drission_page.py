import time
import os
from typing import Generator, Dict, Any, List
from DrissionPage import ChromiumPage, ChromiumOptions
from app.domain.models import Platform, LoginStatus
from app.application.interfaces import AutomationService

from app.infrastructure.automation.platforms.facebook import login_facebook
from app.infrastructure.automation.platforms.youtube import login_youtube
from app.infrastructure.automation.platforms.tiktok import login_tiktok
from app.infrastructure.automation.platforms.twitter import login_twitter

class DrissionPageAutomationService(AutomationService):
    def run_login(
        self,
        username: str,
        password: str,
        platform: Platform,
        profile_key: str
    ) -> Generator[Dict[str, Any], None, None]:
        
        # Initialize execution logs
        execution_logs: List[str] = []
        
        def log(msg: str):
            execution_logs.append(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] {msg}")
            return {"type": "log", "message": msg}

        yield log("Đang khởi tạo trình duyệt qua GemLogin API...")
        
        # Load environment variables for configuration
        from dotenv import load_dotenv
        load_dotenv()
        gemlogin_api_url = os.getenv("GEMLOGIN_API_URL", "http://127.0.0.1:1010/api")
        gemlogin_profile_id = os.getenv("GEMLOGIN_PROFILE_ID")
        gemlogin_profile_name = os.getenv("GEMLOGIN_PROFILE_NAME")
        
        page = None
        profile_id = None
        final_status_val = LoginStatus.LOGGED_OUT
        
        try:
            import requests
            import re

            # Determine profile_id to use
            if gemlogin_profile_id:
                profile_id = gemlogin_profile_id
                yield log(f"Sử dụng GemLogin Profile ID cố định cấu hình từ .env: {profile_id}")
            else:
                # If gemlogin_profile_name is not configured, fall back to "default"
                search_name = gemlogin_profile_name or "default"
                yield log(f"Đang kiểm tra danh sách profile trên GemLogin để tìm profile tên '{search_name}'...")
                try:
                    res = requests.get(f"{gemlogin_api_url}/profiles", timeout=10)
                    res.raise_for_status()
                    profiles = res.json()
                    if isinstance(profiles, dict) and "data" in profiles:
                        profiles_list = profiles["data"]
                    elif isinstance(profiles, list):
                        profiles_list = profiles
                    else:
                        profiles_list = []
                except Exception as e_profiles:
                    yield log(f"Không thể kết nối tới GemLogin API (Hãy đảm bảo ứng dụng GemLogin đang chạy trên cổng 1010): {str(e_profiles)}")
                    raise e_profiles

                # Search for profile by name
                for p in profiles_list:
                    p_name = p.get("name") if isinstance(p, dict) else None
                    if p_name == search_name:
                        profile_id = p.get("id") or p.get("_id")
                        break

                if profile_id:
                    yield log(f"Tìm thấy profile GemLogin '{search_name}' với ID: {profile_id}")
                else:
                    err_msg = f"Không tìm thấy profile '{search_name}' trên GemLogin và hệ thống đã cấu hình không tự động tạo mới."
                    yield log(err_msg)
                    raise ValueError(err_msg)

            # 2. Start the profile via API
            yield log(f"Đang mở trình duyệt cho profile ID: {profile_id}...")
            try:
                res_start = requests.get(f"{gemlogin_api_url}/profiles/start/{profile_id}", timeout=20)
                res_start.raise_for_status()
                start_data = res_start.json()
            except Exception as e_start:
                yield log(f"Lỗi khi gọi API mở profile: {str(e_start)}")
                raise e_start

            # Extract debugging port
            port = None
            if isinstance(start_data, dict):
                if "port" in start_data:
                    port = int(start_data["port"])
                elif "data" in start_data and isinstance(start_data["data"], dict) and "port" in start_data["data"]:
                    port = int(start_data["data"]["port"])
                else:
                    # Search for port inside ws, wsUrl, selenium, remote_debugging_address, etc.
                    for key in ["ws", "wsUrl", "selenium", "debuggerAddress", "browserWSEndpoint", "remote_debugging_address"]:
                        val = start_data.get(key)
                        if not val and "data" in start_data and isinstance(start_data["data"], dict):
                            val = start_data["data"].get(key)
                        if val and isinstance(val, str):
                            match = re.search(r':(\d+)', val)
                            if match:
                                port = int(match.group(1))
                                break

            if not port:
                yield log(f"Không thể tìm thấy cổng debugging từ phản hồi API: {start_data}")
                raise ValueError("Không tìm thấy cổng debugging.")

            yield log(f"Đang kết nối DrissionPage tới cổng debug của trình duyệt: {port}...")
            co = ChromiumOptions()
            co.set_local_port(port)
            page = ChromiumPage(addr_or_opts=co)
            
            if platform == Platform.FACEBOOK:
                final_status_val = yield from login_facebook(page, username, password, log)
            elif platform == Platform.YOUTUBE:
                final_status_val = yield from login_youtube(page, username, password, log)
            elif platform == Platform.TIKTOK:
                final_status_val = yield from login_tiktok(page, username, password, log)
            elif platform == Platform.TWITTER:
                final_status_val = yield from login_twitter(page, username, password, log)
            else:
                yield log(f"Nền tảng {platform} chưa được hỗ trợ.")
                final_status_val = LoginStatus.LOGGED_OUT

        except Exception as e:
            yield log(f"Lỗi hệ thống khi tự động hóa: {str(e)}")
            final_status_val = LoginStatus.LOGGED_OUT
        finally:
            if page:
                try:
                    current_file_dir = os.path.dirname(os.path.abspath(__file__))
                    backend_dir = os.path.dirname(os.path.dirname(os.path.dirname(current_file_dir)))
                    screenshots_dir = os.path.join(backend_dir, "screenshots")
                    os.makedirs(screenshots_dir, exist_ok=True)
                    
                    timestamp = int(time.time())
                    screenshot_name = f"{profile_key}_{timestamp}.png"
                    screenshot_path = os.path.join(screenshots_dir, screenshot_name)
                    
                    page.get_screenshot(path=screenshot_path, full_page=False)
                    yield log(f"Đã chụp ảnh màn hình lưu tại: backend/screenshots/{screenshot_name}")
                except Exception as e_ss:
                    yield log(f"Không thể chụp ảnh màn hình: {str(e_ss)}")

                yield log("Đang tắt trình duyệt...")
                try:
                    # Let the browser window stay open for 3 seconds so user can see final state
                    time.sleep(3)
                    
                    # Close via GemLogin API
                    if profile_id:
                        yield log(f"Đang đóng profile GemLogin {profile_id}...")
                        try:
                            close_res = requests.get(f"{gemlogin_api_url}/profiles/close/{profile_id}", timeout=10)
                            yield log(f"Đã đóng profile: {close_res.json()}")
                        except Exception as e_close:
                            yield log(f"Không thể gọi API đóng profile: {str(e_close)}")
                    
                    try:
                        page.quit()
                    except Exception:
                        pass
                    yield log("Trình duyệt đã đóng.")
                except Exception as ex:
                    yield log(f"Không thể đóng trình duyệt sạch sẽ: {str(ex)}")

            # Send final results package exactly once
            yield {"type": "result", "status": final_status_val, "logs": "\n".join(execution_logs)}
