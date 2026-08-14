# File: backend/app/infrastructure/ai/gemini_schemas.py
"""Strict Gemini structured-inference wire schemas."""

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.infrastructure.ai.status_policy import WireAssessment


class GeminiSelectorWire(BaseModel):
    model_config = ConfigDict(extra="forbid")
    selector: str | None = Field(default=None, max_length=500)
    confidence: float = Field(ge=0, le=1)
    reasoning: str = Field(max_length=500)

    @field_validator("selector")
    @classmethod
    def normalize_selector(cls, value: str | None) -> str | None:
        return value.strip() if value and value.strip() else None


class GeminiSelectorBatchItemWire(GeminiSelectorWire):
    intent: str = Field(min_length=1, max_length=100)


class GeminiSelectorBatchWire(BaseModel):
    model_config = ConfigDict(extra="forbid")
    selectors: list[GeminiSelectorBatchItemWire] = Field(min_length=1, max_length=10)


__all__ = ["GeminiSelectorBatchWire", "GeminiSelectorWire", "WireAssessment"]
