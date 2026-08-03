# File: backend/app/application/use_cases/run_login.py
"""Unified automation run execution use case supporting both single account and batch account runs."""

import asyncio
import logging
import threading
from typing import Generator, Dict, Any, Optional, List, AsyncGenerator

from app.domain.models import LoginHistory, LoginStatus
from app.domain.repositories import AccountRepository, LoginHistoryRepository
from app.application.interfaces import AutomationService

logger = logging.getLogger(__name__)


class RunLoginUseCase:
    """
    Unified use case for executing social media automation tasks.
    Supports single account execution via execute() and multi-account batch execution via execute_batch().
    """

    def __init__(
        self,
        account_repo: AccountRepository,
        history_repo: LoginHistoryRepository,
        automation_service: AutomationService,
        max_concurrent: int = 3,
        session_factory: Any = None
    ):
        self.account_repo = account_repo
        self.history_repo = history_repo
        self.automation_service = automation_service
        self.max_concurrent = max_concurrent
        # A session factory is needed only for concurrent batch execution.
        # Resolve the infrastructure dependency lazily so single-login tests
        # remain independent of SQLAlchemy.
        self.session_factory = session_factory

    def execute(
        self,
        account_id: int,
        profile_name: Optional[str] = None,
        cancellation_event: Optional[threading.Event] = None,
    ) -> Generator[Dict[str, Any], None, None]:
        """
        Execute login automation for a single account.
        
        Args:
            account_id: Database ID of target account.
            profile_name: Optional specific GemLogin profile name to override. If None,
                          uses account.gemlogin_profile_name or default slot profile '1'.
        """
        account = self.account_repo.get_by_id(account_id)
        if not account:
            yield {"type": "error", "message": f"Tài khoản ID {account_id} không tồn tại."}
            return

        yield {"type": "log", "message": f"Bắt đầu chạy automation đăng nhập cho {account.platform.value} ({account.username})..."}
        
        final_status = None
        full_logs = ""
        
        try:
            profile_key = f"{account.platform.value}_{account.id}"
            # Default to configured profile name or default slot profile "1"
            target_profile_name = profile_name or account.gemlogin_profile_name or "1"
            run_kwargs = {}
            if cancellation_event is not None:
                run_kwargs["cancellation_event"] = cancellation_event
            automation_run = iter(self.automation_service.run_login(
                account.username,
                account.password,
                account.platform,
                profile_key,
                target_profile_name,
                **run_kwargs,
            ))
            while True:
                if cancellation_event and cancellation_event.is_set():
                    close = getattr(automation_run, "close", None)
                    if callable(close):
                        close()
                    yield {"type": "cancelled", "message": "Automation was cancelled because the client disconnected."}
                    return

                try:
                    progress = next(automation_run)
                except StopIteration:
                    break

                if progress["type"] == "log":
                    yield progress
                elif progress["type"] == "result":
                    final_status = progress["status"]
                    full_logs = progress["logs"]
                    yield progress
        except Exception as e:
            error_msg = f"Lỗi không mong muốn trong quá trình chạy: {str(e)}"
            yield {"type": "log", "message": error_msg}
            final_status = LoginStatus.LOGGED_OUT
            full_logs = f"System Error:\n{str(e)}"
            yield {"type": "result", "status": final_status, "logs": full_logs}

        if final_status:
            status_enum = LoginStatus(final_status)
            
            # Update account status
            account.update_status(status_enum)
            self.account_repo.save(account)
            
            # Save history log
            history = LoginHistory(
                id=None,
                account_id=account.id,
                platform=account.platform,
                status=status_enum,
                run_logs=full_logs
            )
            self.history_repo.save(history)
            
            yield {"type": "log", "message": f"Đã cập nhật trạng thái tài khoản '{account.username}' thành: {status_enum.value}."}
            yield {"type": "done", "message": "Hoàn thành automation."}

    async def execute_batch(self, account_ids: List[int]) -> AsyncGenerator[Dict[str, Any], None]:
        """
        Execute login automation for multiple accounts concurrently.
        
        Args:
            account_ids: List of target account database IDs.
        """
        if self.max_concurrent < 1:
            raise ValueError("max_concurrent must be at least 1")

        unique_account_ids = list(dict.fromkeys(account_ids))
        valid_accounts = []
        for account_id in unique_account_ids:
            account = self.account_repo.get_by_id(account_id)
            if not account:
                yield {
                    "type": "error",
                    "account_id": account_id,
                    "message": f"Tài khoản ID {account_id} không tồn tại."
                }
            else:
                valid_accounts.append(account)

        if not valid_accounts:
            return

        event_queue = asyncio.Queue()
        loop = asyncio.get_running_loop()
        session_factory = self.session_factory
        if session_factory is None:
            from app.infrastructure.database.connection import SessionLocal
            session_factory = SessionLocal

        # Slot pool of profile names corresponding to slots: "1", "2", ..., "max_concurrent"
        profile_pool = asyncio.Queue()
        for i in range(1, self.max_concurrent + 1):
            profile_pool.put_nowait(str(i))

        assigned_profiles = {}
        results = {}
        cancellation_events: dict[int, threading.Event] = {}

        async def run_worker(account_id: int):
            profile_name: Optional[str] = None
            cancellation_event = threading.Event()
            cancellation_events[account_id] = cancellation_event
            try:
                profile_name = await profile_pool.get()
                assigned_profiles[account_id] = profile_name
                await event_queue.put({
                    "type": "task_started",
                    "account_id": account_id,
                    "message": f"Bắt đầu chạy trên profile GemLogin slot: {profile_name}...",
                    "assigned_profile": profile_name
                })

                def thread_worker():
                    # Create thread-local database session to avoid thread-safety violations in SQLAlchemy
                    session = session_factory()
                    try:
                        from app.infrastructure.database.repositories import (
                            SqlAlchemyAccountRepository,
                            SqlAlchemyLoginHistoryRepository
                        )
                        thread_account_repo = SqlAlchemyAccountRepository(session)
                        thread_history_repo = SqlAlchemyLoginHistoryRepository(session)

                        single_use_case = RunLoginUseCase(
                            account_repo=thread_account_repo,
                            history_repo=thread_history_repo,
                            automation_service=self.automation_service
                        )
                        for progress in single_use_case.execute(
                            account_id,
                            profile_name=profile_name,
                            cancellation_event=cancellation_event,
                        ):
                            progress_with_id = {**progress, "account_id": account_id}
                            loop.call_soon_threadsafe(event_queue.put_nowait, progress_with_id)
                    except Exception as e:
                        err_evt = {
                            "type": "error",
                            "account_id": account_id,
                            "message": f"Lỗi nghiêm trọng: {str(e)}"
                        }
                        loop.call_soon_threadsafe(event_queue.put_nowait, err_evt)
                    finally:
                        session.close()

                await asyncio.to_thread(thread_worker)
                
                await event_queue.put({
                    "type": "task_completed",
                    "account_id": account_id,
                    "message": "Hoàn tất."
                })
            except asyncio.CancelledError:
                cancellation_event.set()
                event_queue.put_nowait({
                    "type": "task_cancelled",
                    "account_id": account_id,
                    "message": "Client disconnected; stopping automation safely."
                })
                raise
            finally:
                if profile_name is not None:
                    profile_pool.put_nowait(profile_name)
                    profile_pool.task_done()

        # Yield initially that all accounts are queued
        for account in valid_accounts:
            yield {
                "type": "task_queued",
                "account_id": account.id,
                "username": account.username,
                "platform": account.platform.value,
                "message": "Đang trong hàng đợi..."
            }

        workers = [asyncio.create_task(run_worker(acc.id)) for acc in valid_accounts]

        async def wait_for_all():
            await asyncio.gather(*workers, return_exceptions=True)
            await event_queue.put(None)

        completion_task = asyncio.create_task(wait_for_all())
        completed_normally = False
        try:
            while True:
                event = await event_queue.get()
                if event is None:
                    break

                if event.get("type") == "result":
                    results[event["account_id"]] = {
                        "status": event.get("status"),
                        "logs": event.get("logs")
                    }

                yield event
            completed_normally = True
        finally:
            if not completed_normally:
                for cancellation_event in cancellation_events.values():
                    cancellation_event.set()
                for worker in workers:
                    if not worker.done():
                        worker.cancel()
                if not completion_task.done():
                    completion_task.cancel()
                await asyncio.gather(*workers, return_exceptions=True)
                await asyncio.gather(completion_task, return_exceptions=True)

        success_count = sum(
            1
            for result in results.values()
            if result["status"] == LoginStatus.LOGGED_IN or result["status"] == LoginStatus.LOGGED_IN.value
        )
        summary = {
            "type": "batch_summary",
            "total": len(valid_accounts),
            "success_count": success_count,
            "error_count": len(valid_accounts) - success_count,
            "details": {
                aid: {
                    "username": next((a.username for a in valid_accounts if a.id == aid), "Unknown"),
                    "platform": next((a.platform.value for a in valid_accounts if a.id == aid), "Unknown"),
                    "status": r["status"].value if hasattr(r["status"], "value") else str(r["status"]),
                    "gemlogin_profile_name": assigned_profiles.get(aid, "Mặc định"),
                    "logs": r["logs"]
                }
                for aid, r in results.items()
            }
        }
        yield summary
