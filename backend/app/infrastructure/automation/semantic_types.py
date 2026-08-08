# File: backend/app/infrastructure/automation/semantic_types.py
"""Immutable contracts for semantic browser-element resolution."""

from dataclasses import dataclass
from enum import Enum
from typing import Generic, TypeVar


class SemanticIntent(str, Enum):
    EMAIL_OR_PHONE_INPUT = "email_or_phone_input"
    PASSWORD_INPUT = "password_input"
    CONTINUE_CONTROL = "continue_control"
    LOGIN_SUBMIT_CONTROL = "login_submit_control"


class ResolutionSource(str, Enum):
    AI = "ai"
    REGISTRY = "registry"
    NONE = "none"


class ResolutionFailure(str, Enum):
    NONE = "none"
    CANCELLED = "cancelled"
    REGISTRY_MISSING = "registry_missing"
    EVIDENCE_UNAVAILABLE = "evidence_unavailable"
    AI_DISABLED = "ai_disabled"
    AI_REJECTED = "ai_rejected"
    NOT_FOUND = "not_found"
    UNEXPECTED_ERROR = "unexpected_error"


@dataclass(frozen=True, slots=True)
class LocatorSpec:
    hint_text: str
    selectors: tuple[str, ...]
    timeout_seconds: float

    def __post_init__(self) -> None:
        if not self.hint_text.strip() or not self.selectors:
            raise ValueError("Locator specs require a hint and selectors")
        if any(not selector.strip() for selector in self.selectors):
            raise ValueError("Locator selectors must not be empty")
        if len(set(self.selectors)) != len(self.selectors):
            raise ValueError("Locator selectors must be unique")
        if not 0 < self.timeout_seconds <= 10:
            raise ValueError("Locator timeout is outside the allowed range")


TElement = TypeVar("TElement")


@dataclass(frozen=True, slots=True)
class SemanticResolution(Generic[TElement]):
    element: TElement | None
    source: ResolutionSource
    failure: ResolutionFailure
    ai_attempts: int = 0
    confidence: float = 0.0
    reason: str = ""

    def __post_init__(self) -> None:
        if not 0 <= self.ai_attempts <= 2 or not 0 <= self.confidence <= 1:
            raise ValueError("Invalid semantic resolution metrics")
        if len(self.reason) > 240:
            raise ValueError("Semantic resolution reason is too long")
        if self.element is not None and (
            self.source == ResolutionSource.NONE or self.failure != ResolutionFailure.NONE
        ):
            raise ValueError("Resolved elements require a successful source")
        if self.element is None and (
            self.source != ResolutionSource.NONE or self.failure == ResolutionFailure.NONE
        ):
            raise ValueError("Unresolved results require a failure")
