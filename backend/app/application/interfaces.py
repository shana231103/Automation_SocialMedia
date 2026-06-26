from abc import ABC, abstractmethod
from typing import Generator, Any
from app.domain.models import Platform

class BrowserContextManager(ABC):
    @abstractmethod
    def get_new_logs(self) -> list[str]:
        """Returns new logs accumulated since last call."""
        pass

    @abstractmethod
    def __enter__(self) -> Any:
        """Enters the context and returns the page object."""
        pass

    @abstractmethod
    def __exit__(self, exc_type: type[BaseException] | None, exc_val: BaseException | None, exc_tb: Any) -> bool:
        """Exits the context and performs cleanup."""
        pass

class AutomationService(ABC):
    @abstractmethod
    def run_login(
        self,
        username: str,
        password: str,
        platform: Platform,
        profile_key: str
    ) -> Generator[dict[str, Any], None, None]:
        """
        Runs the login automation.
        Yields dictionaries representing progress update:
        - {"type": "log", "message": "Step description"}
        - {"type": "result", "status": "đã đăng nhập", "logs": "Full execution log"}
        """
        pass
