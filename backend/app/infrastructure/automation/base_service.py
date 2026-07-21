import time
import traceback
from typing import Generator, Any, Callable, Type
from app.domain.models import Platform, LoginStatus
from app.application.interfaces import AutomationService, BrowserContextManager
from app.infrastructure.automation.page_wrapper import AutomationPage
from app.infrastructure.automation.actions import ACTION_REGISTRY


class BaseAutomationService(AutomationService):
    """
    Base service implementing AutomationService interface to execute browser automation actions.
    Consolidates run flow execution, error handling, logging, and browser lifecycle wrapper setup.
    """
    _browser_manager_factory: Callable[[str, str | None], BrowserContextManager]
    _page_wrapper_class: Type[AutomationPage]

    def __init__(
        self,
        browser_manager_factory: Callable[[str, str | None], BrowserContextManager],
        page_wrapper_class: Type[AutomationPage],
    ):
        self._browser_manager_factory = browser_manager_factory
        self._page_wrapper_class = page_wrapper_class

    def run_login(
        self, username: str, password: str, platform: Platform, profile_key: str, profile_name: str | None = None
    ) -> Generator[dict[str, Any], None, None]:
        # Delegate to run_action for backward compatibility
        params = {
            "username": username,
            "password": password,
            "platform": platform
        }
        yield from self.run_action("login", params, profile_key, profile_name)

    def run_action(
        self, action_name: str, params: dict[str, Any], profile_key: str, profile_name: str | None = None
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
            yield log(f"Hành động '{action_name}' không được đăng ký trong hệ thống.")
            yield {
                "type": "result",
                "status": final_status_val,
                "logs": "\n".join(execution_logs),
            }
            return

        browser_manager = self._browser_manager_factory(profile_key, profile_name)

        try:
            with browser_manager as native_page:
                # Yield setup logs
                for log_msg in browser_manager.get_new_logs():
                    yield log(log_msg)

                page = self._page_wrapper_class(native_page)
                action_instance = action_class()
                
                # Execute action strategy
                final_status_val = yield from action_instance.execute(
                    page, params, log
                )

        except Exception as e:
            # Yield any logs that were added during setup or before raising the error
            for log_msg in browser_manager.get_new_logs():
                yield log(log_msg)
            
            tb_str = traceback.format_exc()
            yield log(f"Lỗi hệ thống khi tự động hóa hành động '{action_name}': {str(e)}\n{tb_str}")
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
