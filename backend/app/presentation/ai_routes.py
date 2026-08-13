# File: backend/app/presentation/ai_routes.py
"""Provider-neutral AI health endpoint."""

from dataclasses import asdict

from fastapi import APIRouter, Depends

from app.application.ai_login import AILoginRuntime
from app.infrastructure.ai.factory import get_ai_composition


router = APIRouter()


def get_ai_runtime() -> AILoginRuntime:
    return get_ai_composition()[1]


@router.get("/ai/status")
def get_ai_status(runtime: AILoginRuntime = Depends(get_ai_runtime)) -> dict[str, object]:
    return asdict(runtime.health.get_health())
