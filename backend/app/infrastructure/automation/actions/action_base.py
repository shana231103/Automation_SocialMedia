# File: backend/app/infrastructure/automation/actions/action_base.py
"""Abstract base action command interface for browser automation."""

from abc import ABC, abstractmethod
from typing import Any, Callable
from app.infrastructure.automation.page_wrapper import AutomationPage


class AutomationAction(ABC):
    """
    Abstract base action class that encapsulates a specific browser feature.

    Subclasses must implement execute(). Actions are completely driver-agnostic
    and interact with the browser solely via the AutomationPage wrapper.
    """

    @abstractmethod
    def execute(
        self,
        page: AutomationPage,
        params: dict[str, Any],
        log_func: Callable[[str], dict[str, Any]]
    ) -> Any:
        """
        Execute the browser automation steps for this action.

        Args:
            page:     The driver-agnostic AutomationPage wrapper.
            params:   A dictionary containing credentials, configurations, etc.
            log_func: Callback function to format and yield SSE progress logs.

        Returns:
            The final result of the action (e.g. LoginStatus, ActionStatus).
        """
        pass
