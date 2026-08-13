# File: backend/app/infrastructure/ai/provider_errors.py
"""Normalize provider exceptions without exposing response bodies or credentials."""

from app.application.ai_login import AIFailureCode


def map_provider_error(exc: Exception) -> tuple[AIFailureCode, str]:
    name = type(exc).__name__.lower()
    status = getattr(exc, "status_code", None)
    if status == 401 or "authentication" in name:
        return AIFailureCode.AUTH, "Provider authentication failed"
    if status == 403 or "permission" in name:
        return AIFailureCode.PERMISSION, "Provider permission denied"
    if status == 404 or "notfound" in name:
        return AIFailureCode.MODEL_MISSING, "Configured model is unavailable"
    if status == 429 or "ratelimit" in name:
        return AIFailureCode.RATE_LIMIT, "Provider rate limit reached"
    if "timeout" in name:
        return AIFailureCode.TIMEOUT, "Provider request timed out"
    if isinstance(status, int) and status >= 500:
        return AIFailureCode.UNAVAILABLE, "Provider service is unavailable"
    if "connection" in name or "network" in name:
        return AIFailureCode.UNAVAILABLE, "Provider network request failed"
    return AIFailureCode.INVALID_RESPONSE, "Provider response could not be processed"

