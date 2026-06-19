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

        yield log("Đang khởi tạo trình duyệt Chrome...")
        
        page = None
        final_status_val = LoginStatus.LOGGED_OUT
        try:
            # Set chromium options
            co = ChromiumOptions()
            co.set_argument("--disable-gpu")
            # Clear standard automation flags to evade detection
            co.set_argument("--disable-blink-features=AutomationControlled")
            
            # Avoid profile lock by using custom user data dir inside the project directory
            current_dir = os.path.dirname(os.path.abspath(__file__))
            user_data_path = os.path.join(current_dir, "chrome_profiles", profile_key)
            os.makedirs(user_data_path, exist_ok=True)
            co.set_paths(user_data_path=user_data_path)

            # Start the headed browser (visible)
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
                    page.quit()
                    yield log("Trình duyệt đã đóng.")
                except Exception as ex:
                    yield log(f"Không thể đóng trình duyệt sạch sẽ: {str(ex)}")

            # Send final results package exactly once
            yield {"type": "result", "status": final_status_val, "logs": "\n".join(execution_logs)}
