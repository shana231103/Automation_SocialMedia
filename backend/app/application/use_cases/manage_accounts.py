from typing import List, Optional
from app.domain.models import Account, Platform, LoginStatus
from app.domain.repositories import AccountRepository

class GetAccountsUseCase:
    def __init__(self, account_repo: AccountRepository):
        self.account_repo = account_repo

    def execute(self) -> List[Account]:
        return self.account_repo.get_all()

class CreateAccountUseCase:
    def __init__(self, account_repo: AccountRepository):
        self.account_repo = account_repo

    def execute(self, username: str, password: str, platform: Platform) -> Account:
        account = Account(
            id=None,
            username=username,
            password=password,
            platform=platform,
            status=LoginStatus.LOGGED_OUT,
            last_checked_at=None
        )
        return self.account_repo.save(account)

class DeleteAccountUseCase:
    def __init__(self, account_repo: AccountRepository):
        self.account_repo = account_repo

    def execute(self, account_id: int) -> bool:
        return self.account_repo.delete(account_id)
