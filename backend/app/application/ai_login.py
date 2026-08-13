# File: backend/app/application/ai_login.py
"""Provider-neutral contracts for AI-assisted login automation."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import Enum
import threading

from app.domain.models import LoginStatus, Platform


class AIProviderName(str, Enum):
    DISABLED = "disabled"
    GEMINI = "gemini"
    OPENAI = "openai"


class AILoginStrategy(str, Enum):
    DISABLED = "disabled"
    SEMANTIC = "semantic"


class AICapability(str, Enum):
    SELECTOR = "selector"
    TERMINAL_ASSESSMENT = "terminal_assessment"


class AIFailureCode(str, Enum):
    DISABLED = "disabled"
    CANCELLED = "cancelled"
    CONFIGURATION = "configuration"
    AUTH = "auth"
    PERMISSION = "permission"
    RATE_LIMIT = "rate_limit"
    TIMEOUT = "timeout"
    UNAVAILABLE = "unavailable"
    MODEL_MISSING = "model_missing"
    VISION_UNSUPPORTED = "vision_unsupported"
    CAPABILITY_UNSUPPORTED = "capability_unsupported"
    INVALID_RESPONSE = "invalid_response"
    PAYLOAD_TOO_LARGE = "payload_too_large"
    BUDGET_EXHAUSTED = "budget_exhausted"


class VerificationOutcome(str, Enum):
    SKIPPED_LOGGED_IN = "skipped_logged_in"
    SKIPPED_DISABLED = "skipped_disabled"
    CONFIRMED = "confirmed"
    OVERRIDDEN = "overridden"
    REJECTED = "rejected"
    FALLBACK = "fallback"
    CANCELLED = "cancelled"
    REUSED = "reused"


@dataclass(frozen=True)
class ProtectedObservation:
    observation_id: str
    platform: Platform
    redacted_url: str
    screenshot_base64: str
    dom_snippet: str
    preliminary_status: LoginStatus | None = None

@dataclass(frozen=True)
class AIUsage:
    input_tokens: int = 0
    output_tokens: int = 0
    total_tokens: int = 0

    def __post_init__(self) -> None:
        if min(self.input_tokens, self.output_tokens, self.total_tokens) < 0:
            raise ValueError("AI usage cannot be negative")


@dataclass(frozen=True)
class SelectorAssessment:
    selector: str | None = None
    confidence: float = 0.0
    reason: str = ""
    provider: str = "disabled"
    model: str = ""
    usage: AIUsage = AIUsage()
    failure_code: AIFailureCode | None = None

    def __post_init__(self) -> None:
        if not 0 <= self.confidence <= 1 or len(self.reason) > 500:
            raise ValueError("Selector assessment is outside its bounds")
        if self.selector is not None and len(self.selector) > 500:
            raise ValueError("Selector assessment is outside its bounds")


@dataclass(frozen=True)
class TerminalAssessment:
    status: LoginStatus | None
    confidence: float
    reason: str
    observation_id: str
    visual_evidence: tuple[str, ...] = ()
    dom_evidence: tuple[str, ...] = ()
    model_agreement: bool | None = None
    provider: str = "disabled"
    model: str = ""
    usage: AIUsage = AIUsage()
    failure_code: AIFailureCode | None = None

    def __post_init__(self) -> None:
        if not 0 <= self.confidence <= 1 or len(self.reason) > 500:
            raise ValueError("Terminal assessment is outside its bounds")
        if any(not item or len(item) > 200 for item in self.visual_evidence + self.dom_evidence):
            raise ValueError("Terminal evidence is outside its bounds")
        if len(self.visual_evidence) > 5 or len(self.dom_evidence) > 5:
            raise ValueError("Terminal evidence is outside its bounds")
        if self.status is not None and not self.observation_id:
            raise ValueError("Successful terminal assessments require observation identity")

@dataclass(frozen=True)
class StatusVerificationDecision:
    preliminary_status: LoginStatus
    final_status: LoginStatus
    ai_status: LoginStatus | None
    confidence: float | None
    outcome: VerificationOutcome
    reason: str
    duration_ms: int
    provider: str = "disabled"
    model: str = ""
    visual_evidence: tuple[str, ...] = ()
    dom_evidence: tuple[str, ...] = ()
    model_agreement: bool | None = None
    failure_code: AIFailureCode | None = None


@dataclass(frozen=True)
class AIProviderHealth:
    enabled: bool
    provider: str
    strategy: str
    models: tuple[str, ...]
    configured: bool
    reachable: bool | None
    capabilities: tuple[str, ...]
    reason: str


class SelectorInferencePort(ABC):
    @abstractmethod
    def predict_selector(self, observation: ProtectedObservation, intent: str,
                         cancellation_event: threading.Event | None = None) -> SelectorAssessment:
        raise NotImplementedError


class TerminalAssessmentPort(ABC):
    @abstractmethod
    def assess_terminal(self, observation: ProtectedObservation,
                        preliminary_status: LoginStatus,
                        cancellation_event: threading.Event | None = None) -> TerminalAssessment:
        raise NotImplementedError


class AIHealthPort(ABC):
    @abstractmethod
    def get_health(self) -> AIProviderHealth:
        raise NotImplementedError


@dataclass(frozen=True)
class AILoginRuntime:
    selector: SelectorInferencePort | None
    terminal: TerminalAssessmentPort | None
    health: AIHealthPort
    provider: AIProviderName
    strategy: AILoginStrategy
