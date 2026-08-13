# File: backend/app/infrastructure/ai/openai_schemas.py
"""Strict OpenAI Structured Output schemas."""

from pydantic import BaseModel, ConfigDict, Field, field_validator


class OpenAISelectorWire(BaseModel):
    model_config = ConfigDict(extra="forbid")
    selector: str | None = Field(default=None, max_length=500)
    confidence: float = Field(ge=0, le=1)
    reasoning: str = Field(max_length=500)

    @field_validator("selector")
    @classmethod
    def normalize_selector(cls, value: str | None) -> str | None:
        return value.strip() if value and value.strip() else None


class OpenAIStatusWire(BaseModel):
    model_config = ConfigDict(extra="forbid")
    status: str
    confidence: float = Field(ge=0, le=1)
    reasoning: str = Field(min_length=1, max_length=500)
    agreement: bool
    visual_evidence: list[str] = Field(default_factory=list, max_length=5)
    dom_evidence: list[str] = Field(default_factory=list, max_length=5)

    @field_validator("status")
    @classmethod
    def valid_status(cls, value: str) -> str:
        if value not in {"logged_in", "logged_out", "checkpoint", "dead"}:
            raise ValueError("Invalid login status")
        return value

    @field_validator("visual_evidence", "dom_evidence")
    @classmethod
    def valid_evidence(cls, value: list[str]) -> list[str]:
        if any(not item.strip() or len(item) > 200 for item in value):
            raise ValueError("Invalid evidence item")
        return value

