from abc import ABC, abstractmethod
from typing import List, Optional
from app.domain.models import Account, LoginHistory

class AccountRepository(ABC):
    @abstractmethod
    def get_by_id(self, account_id: int) -> Optional[Account]:
        pass

    @abstractmethod
    def get_all(self) -> List[Account]:
        pass

    @abstractmethod
    def save(self, account: Account) -> Account:
        pass

    @abstractmethod
    def delete(self, account_id: int) -> bool:
        pass


class LoginHistoryRepository(ABC):
    @abstractmethod
    def save(self, history: LoginHistory) -> LoginHistory:
        pass

    @abstractmethod
    def get_all(self) -> List[LoginHistory]:
        pass

    @abstractmethod
    def get_by_account_id(self, account_id: int) -> List[LoginHistory]:
        pass

    @abstractmethod
    def clear_all(self) -> bool:
        pass
