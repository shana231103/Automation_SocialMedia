import sys
import os
import json

# Add backend folder to python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.infrastructure.database.connection import SessionLocal, engine
from app.infrastructure.database.models import Base
from app.infrastructure.database.repositories import SqlAlchemyAccountRepository, SqlAlchemyLoginHistoryRepository
from app.infrastructure.automation.drission_page import DrissionPageAutomationService
from app.application.use_cases.manage_accounts import CreateAccountUseCase
from app.application.use_cases.run_login import RunLoginUseCase
from app.domain.models import Platform

def run_test():
    print("Initializing test database tables...")
    Base.metadata.create_all(bind=engine)
    
    db = SessionLocal()
    try:
        account_repo = SqlAlchemyAccountRepository(db)
        history_repo = SqlAlchemyLoginHistoryRepository(db)
        automation_service = DrissionPageAutomationService()
        
        # 1. Create a mock account for test
        print("\nAdding a mock Facebook account...")
        create_use_case = CreateAccountUseCase(account_repo)
        mock_username = "test_antigravity@gmail.com"
        mock_password = "fakepassword123"
        account = create_use_case.execute(
            username=mock_username,
            password=mock_password,
            platform=Platform.FACEBOOK
        )
        print(f"Mock account created with ID: {account.id}, Username: {account.username}, Status: {account.status.value}")
        
        # 2. Trigger the login automation usecase
        print("\nTriggering login automation for Facebook account...")
        run_use_case = RunLoginUseCase(account_repo, history_repo, automation_service)
        
        # Iterate over progress and print out live steps
        for event in run_use_case.execute(account.id):
            print(f"EVENT: {event}")
            
        # 3. Check final account status in DB
        updated_account = account_repo.get_by_id(account.id)
        print(f"\nFinal Account Status in Database: {updated_account.status.value}")
        
        # 4. Check if a history entry was created
        histories = history_repo.get_by_account_id(account.id)
        print(f"Number of history logs for this account: {len(histories)}")
        if histories:
            latest = histories[0]
            print(f"Latest History Status: {latest.status.value}")
            print(f"Latest History Logs preview:\n{'='*30}\n{latest.run_logs[:400]}...\n{'='*30}")
            
    finally:
        db.close()

if __name__ == "__main__":
    run_test()
