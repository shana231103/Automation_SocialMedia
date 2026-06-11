from abc import ABC, abstractmethod
from typing import Generator, Dict, Any
from app.domain.models import Platform

class AutomationService(ABC):
    @abstractmethod
    def run_login(
        self,
        username: str,
        password: str,
        platform: Platform,
        profile_key: str
    ) -> Generator[Dict[str, Any], None, None]:
        """
        Runs the login automation.
        Yields dictionaries representing progress update:
        - {"type": "log", "message": "Step description"}
        - {"type": "result", "status": "đã đăng nhập", "logs": "Full execution log"}
        """
        pass
