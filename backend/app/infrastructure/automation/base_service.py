import time
import threading
import traceback
from typing import Generator, Any, Callable, Type
from app.domain.models import Platform, LoginStatus
from app.application.interfaces import AutomationService, BrowserContextManager
from app.infrastructure.automation.page_wrapper import AutomationPage
from app.infrastructure.automation.actions import ACTION_REGISTRY
from app.infrastructure.automation.login_status_verification import LoginStatusVerificationCoordinator
from app.infrastructure.automation.login_status_reporting import (
    decision_to_event_metadata, decision_to_log_message,
)


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
        status_verification: LoginStatusVerificationCoordinator | None = None,
    ):
        self._browser_manager_factory = browser_manager_factory
        self._page_wrapper_class = page_wrapper_class
        self._status_verification = status_verification

    def run_login(
        self,
        username: str,
        password: str,
        platform: Platform,
        profile_key: str,
        profile_name: str | None = None,
        cancellation_event: threading.Event | None = None,
    ) -> Generator[dict[str, Any], None, None]:
        # Delegate to run_action for backward compatibility
        params = {
            "username": username,
            "password": password,
            "platform": platform,
            "cancellation_event": cancellation_event
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
        verification_metadata: dict[str, object] | None = None

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

                coordinator = self._status_verification
                cancellation_event = params.get("cancellation_event")
                if (
                    action_name == "login"
                    and coordinator is not None
                    and isinstance(final_status_val, LoginStatus)
                    and coordinator.should_verify(final_status_val, cancellation_event)
                ):
                    yield log("Starting local AI verification of the preliminary login status...")
                    preliminary_status = final_status_val
                    decision = coordinator.resolve(
                        page=page,
                        platform=params["platform"],
                        preliminary_status=preliminary_status,
                        secrets=(str(params.get("username") or ""), str(params.get("password") or "")),
                        cancellation_event=cancellation_event,
                    )
                    final_status_val = decision.final_status
                    verification_metadata = decision_to_event_metadata(decision)
                    yield log(decision_to_log_message(decision))

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
            result_event = {
                "type": "result",
                "status": final_status_val,
                "logs": "\n".join(execution_logs),
            }
            if verification_metadata is not None:
                result_event["verification"] = verification_metadata
            yield result_event
