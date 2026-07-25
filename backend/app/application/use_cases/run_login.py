# File: backend/app/application/use_cases/run_login.py
"""Unified automation run execution use case supporting both single account and batch account runs."""

import asyncio
import logging
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
        if session_factory is None:
            from app.infrastructure.database.connection import SessionLocal
            self.session_factory = SessionLocal
        else:
            self.session_factory = session_factory

    def execute(self, account_id: int, profile_name: Optional[str] = None) -> Generator[Dict[str, Any], None, None]:
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
            for progress in self.automation_service.run_login(
                account.username,
                account.password,
                account.platform,
                profile_key,
                target_profile_name
            ):
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
        valid_accounts = []
        for account_id in account_ids:
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

        # Slot pool of profile names corresponding to slots: "1", "2", ..., "max_concurrent"
        profile_pool = asyncio.Queue()
        for i in range(1, self.max_concurrent + 1):
            profile_pool.put_nowait(str(i))

        assigned_profiles = {}
        results = {}

        async def run_worker(account_id: int):
            profile_name = await profile_pool.get()
            assigned_profiles[account_id] = profile_name
            try:
                await event_queue.put({
                    "type": "task_started",
                    "account_id": account_id,
                    "message": f"Bắt đầu chạy trên profile GemLogin slot: {profile_name}...",
                    "assigned_profile": profile_name
                })

                def thread_worker():
                    # Create thread-local database session to avoid thread-safety violations in SQLAlchemy
                    session = self.session_factory()
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
                        for progress in single_use_case.execute(account_id, profile_name=profile_name):
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
            finally:
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

        asyncio.create_task(wait_for_all())

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

        summary = {
            "type": "batch_summary",
            "total": len(valid_accounts),
            "success_count": sum(1 for r in results.values() if r["status"] == LoginStatus.LOGGED_IN),
            "error_count": sum(1 for r in results.values() if r["status"] != LoginStatus.LOGGED_IN),
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
