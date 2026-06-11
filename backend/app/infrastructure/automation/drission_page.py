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
        platform: Platform
    ) -> Generator[Dict[str, Any], None, None]:
        
        # Initialize execution logs
        execution_logs: List[str] = []
        
        def log(msg: str):
            execution_logs.append(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] {msg}")
            # We will yield this immediately
            return {"type": "log", "message": msg}

        yield log("Đang khởi tạo trình duyệt Chrome...")
        
        page = None
        try:
            # Set chromium options
            co = ChromiumOptions()
            co.set_argument("--disable-gpu")
            # Clear standard automation flags to evade detection
            co.set_argument("--disable-blink-features=AutomationControlled")
            
            # Avoid profile lock by using a custom user data dir inside the project directory
            current_dir = os.path.dirname(os.path.abspath(__file__))
            user_data_path = os.path.join(current_dir, "chrome_profiles", platform.value)
            os.makedirs(user_data_path, exist_ok=True)
            co.set_paths(user_data_path=user_data_path)

            # Start the headed browser (visible)
            page = ChromiumPage(addr_or_opts=co)
            
            if platform == Platform.FACEBOOK:
                yield from login_facebook(page, username, password, log)
            elif platform == Platform.YOUTUBE:
                yield from login_youtube(page, username, password, log)
            elif platform == Platform.TIKTOK:
                yield from login_tiktok(page, username, password, log)
            elif platform == Platform.TWITTER:
                yield from login_twitter(page, username, password, log)
            else:
                yield log(f"Nền tảng {platform} chưa được hỗ trợ.")
                yield {"type": "result", "status": LoginStatus.LOGGED_OUT, "logs": "\n".join(execution_logs)}

        except Exception as e:
            yield log(f"Lỗi hệ thống khi tự động hóa: {str(e)}")
            yield {"type": "result", "status": LoginStatus.LOGGED_OUT, "logs": "\n".join(execution_logs) + f"\nException: {str(e)}"}
        finally:
            if page:
                yield log("Đang tắt trình duyệt...")
                try:
                    # Let the browser window stay open for 3 seconds so user can see final state
                    time.sleep(3)
                    page.quit()
                    yield log("Trình duyệt đã đóng.")
                except Exception as ex:
                    yield log(f"Không thể đóng trình duyệt sạch sẽ: {str(ex)}")

            # Send final results package by searching backwards for the identified status
            final_status_val = LoginStatus.LOGGED_OUT
            for log_line in reversed(execution_logs):
                if "Trạng thái xác định: " in log_line:
                    status_str = log_line.split("Trạng thái xác định: ")[-1].strip()
                    try:
                        final_status_val = LoginStatus(status_str)
                    except ValueError:
                        pass
                    break
            yield {"type": "result", "status": final_status_val, "logs": "\n".join(execution_logs)}
