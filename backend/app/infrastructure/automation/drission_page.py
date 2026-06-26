import time
import os
from typing import Generator, Any, Callable
from app.domain.models import Platform, LoginStatus
from app.application.interfaces import AutomationService, BrowserContextManager

from app.infrastructure.automation.platforms.facebook import login_facebook
from app.infrastructure.automation.platforms.youtube import login_youtube
from app.infrastructure.automation.platforms.tiktok import login_tiktok
from app.infrastructure.automation.platforms.twitter import login_twitter

from app.infrastructure.automation.gemlogin_browser import GemLoginBrowser


def default_browser_manager_factory(profile_key: str) -> BrowserContextManager:
    # pyrefly: ignore [missing-import]
    from dotenv import load_dotenv

    _ = load_dotenv()
    gemlogin_api_url = os.getenv("GEMLOGIN_API_URL", "http://127.0.0.1:1010/api")
    gemlogin_profile_id = os.getenv("GEMLOGIN_PROFILE_ID")
    gemlogin_profile_name = os.getenv("GEMLOGIN_PROFILE_NAME")
    return GemLoginBrowser(
        profile_key=profile_key,
        gemlogin_api_url=gemlogin_api_url,
        gemlogin_profile_id=gemlogin_profile_id,
        gemlogin_profile_name=gemlogin_profile_name,
    )


class DrissionPageAutomationService(AutomationService):
    _browser_manager_factory: Callable[[str], BrowserContextManager]

    def __init__(
        self,
        browser_manager_factory: Callable[[str], BrowserContextManager] | None = None,
    ):
        self._browser_manager_factory = (
            browser_manager_factory or default_browser_manager_factory
        )

    def run_login(
        self, username: str, password: str, platform: Platform, profile_key: str
    ) -> Generator[dict[str, Any], None, None]:

        # Initialize execution logs
        execution_logs: list[str] = []

        def log(msg: str) -> dict[str, Any]:
            execution_logs.append(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] {msg}")
            return {"type": "log", "message": msg}

        final_status_val = LoginStatus.LOGGED_OUT

        browser_manager = self._browser_manager_factory(profile_key)

        try:
            with browser_manager as page:
                # Yield setup logs
                for log_msg in browser_manager.get_new_logs():
                    yield log(log_msg)

                if platform == Platform.FACEBOOK:
                    final_status_val = yield from login_facebook(
                        page, username, password, log
                    )
                elif platform == Platform.YOUTUBE:
                    final_status_val = yield from login_youtube(
                        page, username, password, log
                    )
                elif platform == Platform.TIKTOK:
                    final_status_val = yield from login_tiktok(
                        page, username, password, log
                    )
                elif platform == Platform.TWITTER:
                    final_status_val = yield from login_twitter(
                        page, username, password, log
                    )
                else:
                    yield log(f"Nền tảng {platform} chưa được hỗ trợ.")
                    final_status_val = LoginStatus.LOGGED_OUT

        except Exception as e:
            # Yield any logs that were added during setup or before raising the error
            for log_msg in browser_manager.get_new_logs():
                yield log(log_msg)
            yield log(f"Lỗi hệ thống khi tự động hóa: {str(e)}")
            final_status_val = LoginStatus.LOGGED_OUT
        finally:
            # Yield remaining cleanup logs
            for log_msg in browser_manager.get_new_logs():
                yield log(log_msg)

            # Send final results package exactly once
            yield {
                "type": "result",
                "status": final_status_val,
                "logs": "\n".join(execution_logs),
            }
