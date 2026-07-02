import time
import os
from typing import Generator, Any, Callable
from app.domain.models import Platform, LoginStatus
from app.application.interfaces import AutomationService, BrowserContextManager

from app.infrastructure.automation.adapters import PlaywrightPageWrapper
from app.infrastructure.automation.playwright_browser import GemLoginPlaywrightBrowser
from app.infrastructure.automation.actions import ACTION_REGISTRY

def default_browser_manager_factory(profile_key: str) -> BrowserContextManager:
    from dotenv import load_dotenv
    _ = load_dotenv()
    
    gemlogin_api_url = os.getenv("GEMLOGIN_API_URL", "http://127.0.0.1:1010/api")
    gemlogin_profile_id = os.getenv("GEMLOGIN_PROFILE_ID")
    gemlogin_profile_name = os.getenv("GEMLOGIN_PROFILE_NAME")
    return GemLoginPlaywrightBrowser(
        profile_key=profile_key,
        gemlogin_api_url=gemlogin_api_url,
        gemlogin_profile_id=gemlogin_profile_id,
        gemlogin_profile_name=gemlogin_profile_name,
    )

class PlaywrightAutomationService(AutomationService):
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
        # Delegate to run_action for backward compatibility
        params = {
            "username": username,
            "password": password,
            "platform": platform
        }
        yield from self.run_action("login", params, profile_key)

    def run_action(
        self, action_name: str, params: dict[str, Any], profile_key: str
    ) -> Generator[dict[str, Any], None, None]:
        # Initialize execution logs
        execution_logs: list[str] = []

        def log(msg: str) -> dict[str, Any]:
            execution_logs.append(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] {msg}")
            return {"type": "log", "message": msg}

        final_status_val = LoginStatus.LOGGED_OUT

        # Resolve Action class from registry
        action_class = ACTION_REGISTRY.get(action_name)
        if not action_class:
            yield log(f"Hành động '{action_name}' không được đăng ký trong hệ thống qua Playwright.")
            yield {
                "type": "result",
                "status": final_status_val,
                "logs": "\n".join(execution_logs),
            }
            return

        browser_manager = self._browser_manager_factory(profile_key)

        try:
            with browser_manager as native_page:
                # Yield setup logs
                for log_msg in browser_manager.get_new_logs():
                    yield log(log_msg)

                page = PlaywrightPageWrapper(native_page)
                action_instance = action_class()

                # Execute action strategy
                final_status_val = yield from action_instance.execute(
                    page, params, log
                )

        except Exception as e:
            import traceback
            # Yield any logs that were added during setup or before raising the error
            for log_msg in browser_manager.get_new_logs():
                yield log(log_msg)
            yield log(f"Lỗi hệ thống khi tự động hóa hành động '{action_name}' qua Playwright: {str(e)}\n{traceback.format_exc()}")
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

