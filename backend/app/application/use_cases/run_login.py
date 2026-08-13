# File: backend/app/application/use_cases/run_login.py
"""Single login use case with batch execution delegated to a focused helper."""

import threading
from typing import Any, AsyncGenerator, Generator, Optional

from app.application.interfaces import AutomationService
from app.domain.models import LoginHistory, LoginStatus
from app.domain.repositories import AccountRepository, LoginHistoryRepository


class RunLoginUseCase:
    def __init__(self, account_repo: AccountRepository, history_repo: LoginHistoryRepository,
                 automation_service: AutomationService, max_concurrent: int = 3,
                 session_factory: Any = None) -> None:
        self.account_repo = account_repo
        self.history_repo = history_repo
        self.automation_service = automation_service
        self.max_concurrent = max_concurrent
        self.session_factory = session_factory

    def execute(self, account_id: int, profile_name: Optional[str] = None,
                cancellation_event: Optional[threading.Event] = None,
                ) -> Generator[dict[str, Any], None, None]:
        account = self.account_repo.get_by_id(account_id)
        if not account:
            yield {"type": "error", "message": f"Account ID {account_id} does not exist."}
            return
        yield {"type": "log", "message":
               f"Starting login automation for {account.platform.value} ({account.username})..."}
        final_status = None
        full_logs = ""
        try:
            profile_key = f"{account.platform.value}_{account.id}"
            target_profile = profile_name or account.gemlogin_profile_name or "1"
            kwargs = {"cancellation_event": cancellation_event} if cancellation_event is not None else {}
            automation_run = iter(self.automation_service.run_login(
                account.username, account.password, account.platform, profile_key, target_profile, **kwargs))
            while True:
                if cancellation_event and cancellation_event.is_set():
                    close = getattr(automation_run, "close", None)
                    if callable(close):
                        close()
                    yield {"type": "cancelled",
                           "message": "Automation was cancelled because the client disconnected."}
                    return
                try:
                    progress = next(automation_run)
                except StopIteration:
                    break
                if progress.get("type") == "result":
                    final_status = progress.get("status")
                    full_logs = progress.get("logs", "")
                yield progress
        except Exception:
            message = "Unexpected login automation error; the run failed safely."
            yield {"type": "log", "message": message}
            final_status, full_logs = LoginStatus.LOGGED_OUT, "System Error: safe fallback"
            yield {"type": "result", "status": final_status, "logs": full_logs}
        if final_status is None:
            return
        status = LoginStatus(final_status)
        account.update_status(status)
        self.account_repo.save(account)
        self.history_repo.save(LoginHistory(
            id=None, account_id=account.id, platform=account.platform,
            status=status, run_logs=full_logs))
        yield {"type": "log", "message":
               f"Updated account '{account.username}' to {status.value}."}
        yield {"type": "done", "message": "Automation completed."}

    async def execute_batch(self, account_ids: list[int]) -> AsyncGenerator[dict[str, Any], None]:
        from app.application.use_cases.batch_login_execution import BatchLoginExecution
        async for event in BatchLoginExecution(self).execute(account_ids):
            yield event
