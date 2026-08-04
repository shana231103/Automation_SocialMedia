# File: backend/app/application/status_verification.py
"""Provider-agnostic contracts for post-login account status verification."""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import Enum
import threading

from app.domain.models import LoginStatus, Platform


class VerificationOutcome(str, Enum):
    SKIPPED_LOGGED_IN = "skipped_logged_in"
    SKIPPED_DISABLED = "skipped_disabled"
    CONFIRMED = "confirmed"
    OVERRIDDEN = "overridden"
    REJECTED = "rejected"
    FALLBACK = "fallback"
    CANCELLED = "cancelled"


class VerificationFailureCode(str, Enum):
    DISABLED = "disabled"
    CANCELLED = "cancelled"
    CAPTURE_ERROR = "capture_error"
    PAYLOAD_TOO_LARGE = "payload_too_large"
    UNAVAILABLE = "unavailable"
    TIMEOUT = "timeout"
    MODEL_MISSING = "model_missing"
    VISION_UNSUPPORTED = "vision_unsupported"
    INVALID_RESPONSE = "invalid_response"


@dataclass(frozen=True)
class StatusVerificationEvidence:
    platform: Platform
    preliminary_status: LoginStatus
    sanitized_url: str
    screenshot_base64: str
    dom_snippet: str


@dataclass(frozen=True)
class StatusVerificationAssessment:
    status: LoginStatus | None
    confidence: float
    reasoning: str
    visual_evidence: tuple[str, ...] = ()
    dom_evidence: tuple[str, ...] = ()
    model_agreement: bool | None = None
    failure_code: VerificationFailureCode | None = None
    provider: str = "ollama"
    model: str = ""


@dataclass(frozen=True)
class StatusVerificationDecision:
    preliminary_status: LoginStatus
    final_status: LoginStatus
    ai_status: LoginStatus | None
    confidence: float | None
    outcome: VerificationOutcome
    reason: str
    duration_ms: int
    provider: str = "ollama"
    model: str = ""
    visual_evidence: tuple[str, ...] = ()
    dom_evidence: tuple[str, ...] = ()
    model_agreement: bool | None = None
    failure_code: VerificationFailureCode | None = None


@dataclass(frozen=True)
class StatusVerifierHealth:
    enabled: bool
    provider: str
    model: str
    configured: bool
    reachable: bool | None
    vision_capable: bool | None
    reason: str


class AccountStatusVerifier(ABC):
    """Port implemented by a local multimodal account status classifier."""

    @abstractmethod
    def verify(
        self,
        evidence: StatusVerificationEvidence,
        cancellation_event: threading.Event | None = None,
    ) -> StatusVerificationAssessment:
        """Return an advisory assessment without choosing the final status."""
        raise NotImplementedError

    @abstractmethod
    def get_status(self) -> StatusVerifierHealth:
        """Return safe configuration and readiness information."""
        raise NotImplementedError
