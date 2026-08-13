# File: backend/app/infrastructure/automation/base_service.py
"""Shared browser lifecycle and unified per-login AI orchestration."""

import threading
import time
from typing import Any, Callable, Generator, Type

from app.application.ai_login import AILoginRuntime
from app.application.interfaces import AutomationService, BrowserContextManager
from app.domain.models import LoginStatus, Platform
from app.infrastructure.automation.actions import ACTION_REGISTRY
from app.infrastructure.automation.ai_login_context import AILoginContextFactory
from app.infrastructure.automation.login_status_reporting import (
    decision_to_event_metadata, decision_to_log_message,
)
from app.infrastructure.automation.page_wrapper import AutomationPage
from app.infrastructure.automation.semantic_locator import SemanticLocatorResolver
from app.infrastructure.automation.terminal_status_coordinator import TerminalStatusCoordinator

class BaseAutomationService(AutomationService):
    def __init__(self, browser_manager_factory: Callable[[str, str | None], BrowserContextManager],
                 page_wrapper_class: Type[AutomationPage], ai_runtime: AILoginRuntime,
                 context_factory: AILoginContextFactory) -> None:
        self._browser_manager_factory = browser_manager_factory
        self._page_wrapper_class = page_wrapper_class
        self._runtime = ai_runtime
        self._context_factory = context_factory

    def run_login(self, username: str, password: str, platform: Platform,
                  profile_key: str, profile_name: str | None = None,
                  cancellation_event: threading.Event | None = None,
                  ) -> Generator[dict[str, Any], None, None]:
        params = {"username": username, "password": password, "platform": platform,
                  "cancellation_event": cancellation_event}
        yield from self.run_action("login", params, profile_key, profile_name)

    def run_action(self, action_name: str, params: dict[str, Any], profile_key: str,
                   profile_name: str | None = None) -> Generator[dict[str, Any], None, None]:
        execution_logs: list[str] = []

        def log(message: str) -> dict[str, Any]:
            execution_logs.append(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] {message}")
            return {"type": "log", "message": message}

        final_status = LoginStatus.LOGGED_OUT
        verification: dict[str, object] | None = None
        cancellation = params.get("cancellation_event")
        context = self._context_factory.create(cancellation)
        action_class = ACTION_REGISTRY.get(action_name)
        if action_class is None:
            yield log(f"Hành động '{action_name}' không được đăng ký trong hệ thống.")
            yield {"type": "result", "status": final_status, "logs": "\n".join(execution_logs)}
            return
        browser_manager = self._browser_manager_factory(profile_key, profile_name)
        try:
            with browser_manager as native_page:
                for message in browser_manager.get_new_logs():
                    yield log(message)
                resolver = SemanticLocatorResolver(self._runtime.selector, context)
                page = self._page_wrapper_class(native_page, resolver)
                final_status = yield from action_class().execute(page, params, log)
                if action_name == "login" and not isinstance(final_status, LoginStatus):
                    final_status = LoginStatus(final_status)
                if (action_name == "login" and final_status is not LoginStatus.LOGGED_IN
                        and self._runtime.terminal is not None):
                    coordinator = TerminalStatusCoordinator(self._runtime.terminal, context)
                    decision = coordinator.resolve(
                        page, params["platform"], final_status,
                        (str(params.get("username") or ""), str(params.get("password") or "")), cancellation)
                    final_status = decision.final_status
                    verification = decision_to_event_metadata(decision)
                    yield log(decision_to_log_message(decision))
        except Exception:
            for message in browser_manager.get_new_logs():
                yield log(message)
            yield log(f"Automation action '{action_name}' failed safely.")
            final_status = LoginStatus.LOGGED_OUT
        finally:
            for message in browser_manager.get_new_logs():
                yield log(message)
            result: dict[str, Any] = {"type": "result", "status": final_status,
                                      "logs": "\n".join(execution_logs),
                                      "ai": context.snapshot_metrics().__dict__}
            if verification is not None:
                result["verification"] = verification
            yield result
