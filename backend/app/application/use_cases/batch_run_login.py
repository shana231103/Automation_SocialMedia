# File: backend/app/application/use_cases/batch_run_login.py
import asyncio
import logging
from typing import List, Dict, Any, AsyncGenerator

from app.domain.models import LoginStatus
from app.domain.repositories import AccountRepository, LoginHistoryRepository
from app.application.interfaces import AutomationService
from app.application.use_cases.run_login import RunLoginUseCase

logger = logging.getLogger(__name__)

class BatchRunLoginUseCase:
    def __init__(
        self,
        account_repo: AccountRepository,
        history_repo: LoginHistoryRepository,
        automation_service: AutomationService,
        max_concurrent: int = 3
    ):
        self.account_repo = account_repo
        self.history_repo = history_repo
        self.automation_service = automation_service
        self.max_concurrent = max_concurrent

    async def execute(self, account_ids: List[int]) -> AsyncGenerator[Dict[str, Any], None]:
        # Validate that accounts exist
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

        # Queue to collect logs and results from concurrent tasks
        event_queue = asyncio.Queue()
        loop = asyncio.get_running_loop()

        # Slot pool of profile names corresponding to slots: "1", "2", ..., "max_concurrent"
        profile_pool = asyncio.Queue()
        for i in range(1, self.max_concurrent + 1):
            profile_pool.put_nowait(str(i))

        # Track active profiles and login results
        assigned_profiles = {}
        results = {}

        async def run_worker(account_id: int):
            # 1. Acquire a dynamic profile slot from the queue
            profile_name = await profile_pool.get()
            assigned_profiles[account_id] = profile_name
            try:
                # Notify starting
                await event_queue.put({
                    "type": "task_started",
                    "account_id": account_id,
                    "message": f"Bắt đầu chạy trên profile GemLogin slot: {profile_name}...",
                    "assigned_profile": profile_name
                })

                # 2. Run the synchronous generator of RunLoginUseCase in a thread pool
                def thread_worker():
                    try:
                        run_use_case = RunLoginUseCase(
                            account_repo=self.account_repo,
                            history_repo=self.history_repo,
                            automation_service=self.automation_service
                        )
                        # Pass the dynamically allocated profile_name
                        for progress in run_use_case.execute(account_id, profile_name=profile_name):
                            # Append account_id to the event
                            progress_with_id = {**progress, "account_id": account_id}
                            loop.call_soon_threadsafe(event_queue.put_nowait, progress_with_id)
                    except Exception as e:
                        err_evt = {
                            "type": "error",
                            "account_id": account_id,
                            "message": f"Lỗi nghiêm trọng: {str(e)}"
                        }
                        loop.call_soon_threadsafe(event_queue.put_nowait, err_evt)

                await asyncio.to_thread(thread_worker)
                
                # Notify completion
                await event_queue.put({
                    "type": "task_completed",
                    "account_id": account_id,
                    "message": "Hoàn tất."
                })
            finally:
                # 3. Release profile slot back to pool
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

        # Spawn workers
        workers = [asyncio.create_task(run_worker(acc.id)) for acc in valid_accounts]

        # Monitor worker completions
        async def wait_for_all():
            await asyncio.gather(*workers, return_exceptions=True)
            # Signal the queue that streaming is finished
            await event_queue.put(None)

        asyncio.create_task(wait_for_all())

        # Pull events from queue and yield
        while True:
            event = await event_queue.get()
            if event is None:
                break

            # Capture login results to generate a batch summary
            if event.get("type") == "result":
                results[event["account_id"]] = {
                    "status": event.get("status"),
                    "logs": event.get("logs")
                }

            yield event

        # Build and yield summary
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
