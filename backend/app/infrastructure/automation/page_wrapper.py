# File: backend/app/infrastructure/automation/page_wrapper.py
"""Driver-neutral browser page and element contracts."""

from __future__ import annotations

import threading
from abc import ABC, abstractmethod

from app.domain.models import Platform
from app.infrastructure.automation.semantic_types import SemanticIntent, SemanticResolution


class AutomationElement(ABC):
    """Common operations supported by a resolved page element."""

    @abstractmethod
    def input(self, text: str) -> None:
        raise NotImplementedError

    @abstractmethod
    def click(self, by_js: bool = False) -> None:
        raise NotImplementedError

    @abstractmethod
    def press(self, key: str) -> None:
        raise NotImplementedError

    @abstractmethod
    def exists(self) -> bool:
        raise NotImplementedError


class AutomationPage(ABC):
    """Single-session browser page. Implementations are not thread-safe."""

    @abstractmethod
    def goto(self, url: str) -> None:
        raise NotImplementedError

    @abstractmethod
    def find(self, selector: str, timeout: float = 5.0) -> AutomationElement | None:
        raise NotImplementedError

    @abstractmethod
    def find_first(self, *selectors: str, timeout: float = 5.0) -> AutomationElement | None:
        raise NotImplementedError

    @property
    @abstractmethod
    def url(self) -> str:
        raise NotImplementedError

    @property
    @abstractmethod
    def html(self) -> str:
        raise NotImplementedError

    @abstractmethod
    def capture_screenshot_base64(self, mask_sensitive: bool = True) -> str:
        raise NotImplementedError

    @abstractmethod
    def find_semantic(self, platform: Platform, intent: SemanticIntent,
                      cancellation_event: threading.Event | None = None,
                      ) -> SemanticResolution[AutomationElement]:
        raise NotImplementedError

    def find_semantic_many(self, platform: Platform, intents: tuple[SemanticIntent, ...],
                           cancellation_event: threading.Event | None = None,
                           ) -> dict[SemanticIntent, SemanticResolution[AutomationElement]]:
        return {intent: self.find_semantic(platform, intent, cancellation_event)
                for intent in intents}

    @abstractmethod
    def find_with_ai_fallback(self, selector: str, hint_text: str,
                              timeout: float = 5.0) -> AutomationElement | None:
        raise NotImplementedError
