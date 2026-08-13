# File: backend/app/infrastructure/ai/vision_client.py
"""Compatibility value objects for semantic selector resolution."""

from abc import ABC, abstractmethod
from enum import Enum

from pydantic import BaseModel, ConfigDict, Field, field_validator


class SelectorPredictionFailure(str, Enum):
    NONE = "none"
    DISABLED = "disabled"
    INCOMPLETE_EVIDENCE = "incomplete_evidence"
    TIMEOUT = "timeout"
    UNAVAILABLE = "unavailable"
    HTTP_CLIENT_ERROR = "http_client_error"
    HTTP_SERVER_ERROR = "http_server_error"
    REDIRECT_REFUSED = "redirect_refused"
    RESPONSE_TOO_LARGE = "response_too_large"
    INVALID_RESPONSE = "invalid_response"
    CANCELLED = "cancelled"
    BUDGET_EXHAUSTED = "budget_exhausted"


class ElementPrediction(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    selector: str | None = Field(default=None, max_length=500)
    confidence: float = Field(default=0, ge=0, le=1)
    reasoning: str = Field(default="", max_length=500)
    failure_code: SelectorPredictionFailure = SelectorPredictionFailure.NONE

    @field_validator("selector")
    @classmethod
    def normalize_selector(cls, selector: str | None) -> str | None:
        return selector.strip() if selector and selector.strip() else None


class VisionClient(ABC):
    """Legacy test seam retained while runtime composition uses application ports."""

    @abstractmethod
    def predict_element(self, image_base64: str, dom_snippet: str,
                        hint_text: str) -> ElementPrediction:
        raise NotImplementedError

    @abstractmethod
    def is_enabled(self) -> bool:
        raise NotImplementedError
