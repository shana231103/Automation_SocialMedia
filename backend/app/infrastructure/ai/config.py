# File: backend/app/infrastructure/ai/config.py
"""Validated environment configuration for the selected remote AI provider."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping

from app.application.ai_login import AILoginStrategy, AIProviderName


@dataclass(frozen=True)
class AILimits:
    selector_timeout: float = 20.0
    status_timeout: float = 60.0
    max_selector_attempts: int = 2
    max_calls_per_login: int = 16
    max_concurrent_requests: int = 3
    max_dom_chars: int = 6000
    max_screenshot_bytes: int = 4194304

    @property
    def session_timeout(self) -> float:
        selector_budget = self.selector_timeout * self.max_selector_attempts * 3
        return max(self.status_timeout, selector_budget)


@dataclass(frozen=True)
class AIConfig:
    enabled: bool
    provider: AIProviderName
    strategy: AILoginStrategy
    api_key: str
    model: str
    selector_model: str
    status_model: str
    automation_provider: str
    limits: AILimits
    error: str = ""


def _bool(value: str, name: str) -> bool:
    normalized = value.strip().lower()
    if normalized in {"1", "true", "yes", "on"}:
        return True
    if normalized in {"0", "false", "no", "off"}:
        return False
    raise ValueError(f"{name} must be true or false")


def _number(env: Mapping[str, str], name: str, default: str, minimum: float,
            maximum: float, integer: bool = False) -> float | int:
    raw = env.get(name, default)
    value = int(raw) if integer else float(raw)
    if not minimum <= value <= maximum:
        raise ValueError(f"{name} is outside the allowed range")
    return value


def load_ai_config(env: Mapping[str, str], automation_provider: str) -> AIConfig:
    """Parse only the selected provider's credential and fail closed on invalid input."""
    disabled = AIConfig(False, AIProviderName.DISABLED, AILoginStrategy.DISABLED, "",
                        "", "", "", automation_provider, AILimits())
    try:
        if not _bool(env.get("AI_ENABLED", "false"), "AI_ENABLED"):
            return disabled
        provider = AIProviderName(env.get("AI_PROVIDER", "").strip().lower())
        strategy = AILoginStrategy(env.get("AI_LOGIN_STRATEGY", "semantic").strip().lower())
        if provider is AIProviderName.DISABLED or strategy is not AILoginStrategy.SEMANTIC:
            raise ValueError("Semantic AI provider configuration is required when AI is enabled")
        prefix = "GEMINI" if provider is AIProviderName.GEMINI else "OPENAI"
        api_key = env.get(f"{prefix}_API_KEY", "").strip()
        if not api_key:
            raise ValueError(f"{prefix}_API_KEY is required")
        model = env.get("AI_MODEL", "").strip()
        if not model:
            raise ValueError("AI_MODEL is required")
        limits = AILimits(
            float(_number(env, "AI_SELECTOR_TIMEOUT_SECONDS", "20", 1, 60)),
            float(_number(env, "AI_STATUS_TIMEOUT_SECONDS", "60", 1, 120)),
            int(_number(env, "AI_MAX_SELECTOR_ATTEMPTS", "2", 1, 2, True)),
            int(_number(env, "AI_MAX_CALLS_PER_LOGIN", "16", 1, 50, True)),
            int(_number(env, "AI_MAX_CONCURRENT_REQUESTS", "3", 1, 20, True)),
            int(_number(env, "AI_MAX_DOM_CHARS", "6000", 1000, 12000, True)),
            int(_number(env, "AI_MAX_SCREENSHOT_BYTES", "4194304", 65536, 8388608, True)),
        )
        return AIConfig(True, provider, strategy, api_key,
                        model, env.get("AI_SELECTOR_MODEL", model).strip(),
                        env.get("AI_STATUS_MODEL", model).strip(),
                        automation_provider, limits)
    except (TypeError, ValueError) as exc:
        return AIConfig(**{**disabled.__dict__, "error": str(exc)[:240]})
