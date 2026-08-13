import os
import json
import asyncio
import threading
from typing import List
from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from app.infrastructure.database.connection import get_db, SessionLocal
from app.infrastructure.database.repositories import SqlAlchemyAccountRepository, SqlAlchemyLoginHistoryRepository
from app.infrastructure.automation.drission_page import DrissionPageAutomationService
from app.application.interfaces import AutomationService
from app.application.use_cases.manage_accounts import GetAccountsUseCase, CreateAccountUseCase, DeleteAccountUseCase
from app.application.use_cases.run_login import RunLoginUseCase
from app.application.use_cases.view_history import GetLoginHistoryUseCase, ClearLoginHistoryUseCase
from app.presentation.schemas import AccountCreate, AccountResponse, LoginHistoryResponse
from app.presentation.ai_routes import router as ai_router

router = APIRouter(prefix="/api")
router.include_router(ai_router)

def get_automation_service() -> AutomationService:
    provider = os.getenv("AUTOMATION_PROVIDER", "drissionpage").lower()
    if provider == "playwright":
        from app.infrastructure.automation.playwright_service import PlaywrightAutomationService
        return PlaywrightAutomationService()
    return DrissionPageAutomationService()


@router.get("/accounts", response_model=List[AccountResponse])
def get_accounts(db: Session = Depends(get_db)):
    account_repo = SqlAlchemyAccountRepository(db)
    use_case = GetAccountsUseCase(account_repo)
    return use_case.execute()

@router.post("/accounts", response_model=AccountResponse)
def create_account(account_in: AccountCreate, db: Session = Depends(get_db)):
    account_repo = SqlAlchemyAccountRepository(db)
    use_case = CreateAccountUseCase(account_repo)
    return use_case.execute(
        username=account_in.username,
        password=account_in.password,
        platform=account_in.platform,
        gemlogin_profile_name=account_in.gemlogin_profile_name
    )

@router.delete("/accounts/{account_id}")
def delete_account(account_id: int, db: Session = Depends(get_db)):
    account_repo = SqlAlchemyAccountRepository(db)
    use_case = DeleteAccountUseCase(account_repo)
    success = use_case.execute(account_id)
    if not success:
        raise HTTPException(status_code=404, detail="Không tìm thấy tài khoản để xóa")
    return {"message": "Đã xóa tài khoản thành công"}

@router.get("/history", response_model=List[LoginHistoryResponse])
def get_history(db: Session = Depends(get_db)):
    history_repo = SqlAlchemyLoginHistoryRepository(db)
    use_case = GetLoginHistoryUseCase(history_repo)
    return use_case.execute()

@router.post("/history/clear")
def clear_history(db: Session = Depends(get_db)):
    history_repo = SqlAlchemyLoginHistoryRepository(db)
    use_case = ClearLoginHistoryUseCase(history_repo)
    success = use_case.execute()
    if not success:
        raise HTTPException(status_code=500, detail="Không thể xóa lịch sử")
    return {"message": "Đã xóa lịch sử thành công"}

@router.get("/run-login/{account_id}")
def run_login(account_id: int, request: Request,
              db: Session = Depends(get_db),
              automation_service: AutomationService = Depends(get_automation_service)):
    del db
    async def event_generator():
        cancellation = threading.Event()
        queue: asyncio.Queue = asyncio.Queue()
        loop = asyncio.get_running_loop()

        def run_worker() -> None:
            session = SessionLocal()
            try:
                use_case = RunLoginUseCase(
                    SqlAlchemyAccountRepository(session),
                    SqlAlchemyLoginHistoryRepository(session), automation_service)
                for event in use_case.execute(account_id, cancellation_event=cancellation):
                    loop.call_soon_threadsafe(queue.put_nowait, event)
            except Exception:
                loop.call_soon_threadsafe(queue.put_nowait, {
                    "type": "error", "message": "Login worker failed safely."})
            finally:
                session.close()
                loop.call_soon_threadsafe(queue.put_nowait, None)

        worker = asyncio.create_task(asyncio.to_thread(run_worker))
        try:
            while True:
                if await request.is_disconnected():
                    break
                try:
                    event = await asyncio.wait_for(queue.get(), timeout=.2)
                except asyncio.TimeoutError:
                    continue
                if event is None:
                    break
                yield f"data: {json.dumps(event)}\n\n"
        finally:
            cancellation.set()
            await asyncio.gather(worker, return_exceptions=True)

    return StreamingResponse(event_generator(), media_type="text/event-stream")


@router.get("/batch-login")
def batch_login(
    account_ids: str = Query(..., description="Comma-separated list of account IDs to run"),
    db: Session = Depends(get_db),
    automation_service: AutomationService = Depends(get_automation_service)
):
    try:
        id_list = [int(x.strip()) for x in account_ids.split(",") if x.strip()]
    except ValueError:
        raise HTTPException(status_code=400, detail="Danh sách ID tài khoản không hợp lệ")

    if not id_list or any(account_id <= 0 for account_id in id_list):
        raise HTTPException(status_code=400, detail="Invalid account ID list")

    # Preserve request order while ensuring an account runs at most once per batch.
    id_list = list(dict.fromkeys(id_list))

    try:
        max_concurrent = int(os.getenv("MAX_CONCURRENT_LOGINS", "3"))
        max_batch_size = int(os.getenv("MAX_BATCH_SIZE", "100"))
    except ValueError:
        raise HTTPException(status_code=500, detail="Invalid batch configuration")

    if max_concurrent < 1 or max_batch_size < 1:
        raise HTTPException(status_code=500, detail="Batch configuration values must be positive")
    if len(id_list) > max_batch_size:
        raise HTTPException(status_code=400, detail=f"Batch exceeds the maximum of {max_batch_size} accounts")

    account_repo = SqlAlchemyAccountRepository(db)
    history_repo = SqlAlchemyLoginHistoryRepository(db)

    use_case = RunLoginUseCase(
        account_repo=account_repo,
        history_repo=history_repo,
        automation_service=automation_service,
        max_concurrent=max_concurrent,
        session_factory=SessionLocal
    )

    async def event_generator():
        # Iterate over usecase execution yielding SSE data
        async for event in use_case.execute_batch(id_list):
            yield f"data: {json.dumps(event)}\n\n"

    return StreamingResponse(event_generator(), media_type="text/event-stream")
