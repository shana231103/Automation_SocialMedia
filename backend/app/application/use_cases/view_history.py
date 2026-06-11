from typing import List
from app.domain.models import LoginHistory
from app.domain.repositories import LoginHistoryRepository

class GetLoginHistoryUseCase:
    def __init__(self, history_repo: LoginHistoryRepository):
        self.history_repo = history_repo

    def execute(self) -> List[LoginHistory]:
        return self.history_repo.get_all()

class ClearLoginHistoryUseCase:
    def __init__(self, history_repo: LoginHistoryRepository):
        self.history_repo = history_repo

    def execute(self) -> bool:
        return self.history_repo.clear_all()
