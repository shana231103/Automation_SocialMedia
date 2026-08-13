# File: backend/app/infrastructure/ai/factory.py
"""Single composition path for disabled, Gemini, and OpenAI AI runtimes."""

import os
from functools import lru_cache

from app.application.ai_login import (
    AIHealthPort, AILoginRuntime, AILoginStrategy, AIProviderHealth, AIProviderName,
)
from app.infrastructure.ai.config import AIConfig, load_ai_config
from app.infrastructure.ai.gemini_provider import GeminiProvider
from app.infrastructure.ai.openai_provider import OpenAIProvider
from app.infrastructure.automation.ai_login_context import AILoginContextFactory


class DisabledAIHealth(AIHealthPort):
    def __init__(self, reason: str = "Remote AI is disabled") -> None:
        self.reason = reason

    def get_health(self) -> AIProviderHealth:
        return AIProviderHealth(False, "disabled", "disabled", (), not bool(self.reason), None,
                                (), self.reason)


def build_ai_runtime(config: AIConfig) -> AILoginRuntime:
    if not config.enabled:
        return AILoginRuntime(None, None, DisabledAIHealth(config.error or "Remote AI is disabled"),
                              AIProviderName.DISABLED, AILoginStrategy.DISABLED)
    if config.provider is AIProviderName.GEMINI:
        adapter = GeminiProvider(config.api_key, config.selector_model, config.status_model,
                                  config.limits.selector_timeout,
                                  config.limits.status_timeout)
    else:
        adapter = OpenAIProvider(config.api_key, config.selector_model, config.status_model,
                                 selector_timeout=config.limits.selector_timeout,
                                 status_timeout=config.limits.status_timeout)
    return AILoginRuntime(adapter, adapter, adapter, config.provider, config.strategy)


@lru_cache(maxsize=1)
def get_ai_composition() -> tuple[AIConfig, AILoginRuntime, AILoginContextFactory]:
    automation_provider = os.getenv("AUTOMATION_PROVIDER", "drissionpage").strip().lower()
    config = load_ai_config(os.environ, automation_provider)
    runtime = build_ai_runtime(config)
    return config, runtime, AILoginContextFactory(config.limits)
