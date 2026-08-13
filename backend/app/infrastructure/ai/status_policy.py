# File: backend/app/infrastructure/ai/status_policy.py
"""Strict status response schema and deterministic challenge guard."""

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.application.ai_login import ProtectedObservation
from app.domain.models import LoginStatus


class WireAssessment(BaseModel):
    model_config = ConfigDict(extra="forbid")

    status: Literal["logged_in", "logged_out", "checkpoint", "dead"]
    confidence: float = Field(ge=0.0, le=1.0)
    reasoning: str = Field(min_length=1, max_length=500)
    agreement: bool
    visual_evidence: list[str] = Field(default_factory=list, max_length=5)
    dom_evidence: list[str] = Field(default_factory=list, max_length=5)

    @field_validator("visual_evidence", "dom_evidence")
    @classmethod
    def validate_evidence_items(cls, items: list[str]) -> list[str]:
        if any(not item.strip() or len(item) > 200 for item in items):
            raise ValueError("Evidence items must contain 1-200 characters")
        return items


STATUS_MAP = {
    "logged_in": LoginStatus.LOGGED_IN,
    "logged_out": LoginStatus.LOGGED_OUT,
    "checkpoint": LoginStatus.CHECKPOINT,
    "dead": LoginStatus.DEAD,
}


def hard_evidence_status(observation: ProtectedObservation) -> LoginStatus | None:
    source = f"{observation.redacted_url}\n{observation.dom_snippet}".lower()
    markers = ("checkpoint", "captcha", "challenge", "two-factor", "2fa")
    return LoginStatus.CHECKPOINT if any(marker in source for marker in markers) else None

