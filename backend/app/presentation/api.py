import json
from typing import List
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from app.infrastructure.database.connection import get_db
from app.infrastructure.database.repositories import SqlAlchemyAccountRepository, SqlAlchemyLoginHistoryRepository
from app.infrastructure.automation.drission_page import DrissionPageAutomationService
from app.application.use_cases.manage_accounts import GetAccountsUseCase, CreateAccountUseCase, DeleteAccountUseCase
from app.application.use_cases.run_login import RunLoginUseCase
from app.application.use_cases.view_history import GetLoginHistoryUseCase, ClearLoginHistoryUseCase
from app.presentation.schemas import AccountCreate, AccountResponse, LoginHistoryResponse

router = APIRouter(prefix="/api")

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
        platform=account_in.platform
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
def run_login(account_id: int, db: Session = Depends(get_db)):
    account_repo = SqlAlchemyAccountRepository(db)
    history_repo = SqlAlchemyLoginHistoryRepository(db)
    automation_service = DrissionPageAutomationService()
    
    use_case = RunLoginUseCase(
        account_repo=account_repo,
        history_repo=history_repo,
        automation_service=automation_service
    )
    
    def event_generator():
        # Iterate over usecase execution yielding SSE data
        for event in use_case.execute(account_id):
            yield f"data: {json.dumps(event)}\n\n"

    return StreamingResponse(event_generator(), media_type="text/event-stream")
