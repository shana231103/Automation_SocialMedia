# File: backend/app/application/use_cases/batch_login_execution.py
"""Concurrent batch worker, profile-slot, and multiplexed event coordination."""

import asyncio
import threading
from typing import Any, AsyncGenerator

from app.domain.models import LoginStatus


class BatchLoginExecution:
    def __init__(self, owner: Any) -> None:
        self.owner = owner

    async def execute(self, account_ids: list[int]) -> AsyncGenerator[dict[str, Any], None]:
        if self.owner.max_concurrent < 1:
            raise ValueError("max_concurrent must be at least 1")
        accounts = []
        for account_id in dict.fromkeys(account_ids):
            account = self.owner.account_repo.get_by_id(account_id)
            if account is None:
                yield {"type": "error", "account_id": account_id,
                       "message": f"Account ID {account_id} does not exist."}
            else:
                accounts.append(account)
        if not accounts:
            return
        queue: asyncio.Queue = asyncio.Queue()
        loop = asyncio.get_running_loop()
        session_factory = self.owner.session_factory
        if session_factory is None:
            from app.infrastructure.database.connection import SessionLocal
            session_factory = SessionLocal
        profiles: asyncio.Queue = asyncio.Queue()
        for index in range(1, self.owner.max_concurrent + 1):
            profiles.put_nowait(str(index))
        assignments: dict[int, str] = {}
        results: dict[int, dict[str, Any]] = {}
        cancellations: dict[int, threading.Event] = {}

        async def worker(account_id: int) -> None:
            profile = await profiles.get()
            cancellation = threading.Event()
            cancellations[account_id] = cancellation
            assignments[account_id] = profile
            try:
                await queue.put({"type": "task_started", "account_id": account_id,
                                 "assigned_profile": profile,
                                 "message": f"Started on GemLogin profile slot {profile}."})

                def run_thread() -> None:
                    session = session_factory()
                    try:
                        from app.infrastructure.database.repositories import (
                            SqlAlchemyAccountRepository, SqlAlchemyLoginHistoryRepository,
                        )
                        use_case = type(self.owner)(
                            SqlAlchemyAccountRepository(session),
                            SqlAlchemyLoginHistoryRepository(session),
                            self.owner.automation_service)
                        for event in use_case.execute(account_id, profile, cancellation):
                            loop.call_soon_threadsafe(
                                queue.put_nowait, {**event, "account_id": account_id})
                    except Exception:
                        loop.call_soon_threadsafe(queue.put_nowait, {
                            "type": "error", "account_id": account_id,
                            "message": "Batch worker failed safely."})
                    finally:
                        session.close()

                await asyncio.to_thread(run_thread)
                await queue.put({"type": "task_completed", "account_id": account_id,
                                 "message": "Completed."})
            except asyncio.CancelledError:
                cancellation.set()
                raise
            finally:
                profiles.put_nowait(profile)
                profiles.task_done()

        for account in accounts:
            yield {"type": "task_queued", "account_id": account.id,
                   "username": account.username, "platform": account.platform.value,
                   "message": "Queued."}
        workers = [asyncio.create_task(worker(account.id)) for account in accounts]

        async def finish() -> None:
            await asyncio.gather(*workers, return_exceptions=True)
            await queue.put(None)

        completion = asyncio.create_task(finish())
        completed = False
        try:
            while True:
                event = await queue.get()
                if event is None:
                    break
                if event.get("type") == "result":
                    results[event["account_id"]] = {
                        "status": event.get("status"), "logs": event.get("logs", "")}
                yield event
            completed = True
        finally:
            if not completed:
                for cancellation in cancellations.values():
                    cancellation.set()
                for task in workers + [completion]:
                    if not task.done():
                        task.cancel()
                await asyncio.gather(*workers, completion, return_exceptions=True)
        success = sum(1 for result in results.values()
                      if result["status"] in {LoginStatus.LOGGED_IN, LoginStatus.LOGGED_IN.value})
        yield {"type": "batch_summary", "total": len(accounts), "success_count": success,
               "error_count": len(accounts) - success,
               "details": {account.id: {
                   "username": account.username, "platform": account.platform.value,
                   "status": self._status(results.get(account.id, {}).get("status")),
                   "gemlogin_profile_name": assignments.get(account.id, "Default"),
                   "logs": results.get(account.id, {}).get("logs", "")}
                   for account in accounts}}

    @staticmethod
    def _status(value: Any) -> str:
        return value.value if hasattr(value, "value") else str(value or "error")
