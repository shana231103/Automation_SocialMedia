# File: backend/tests/unit/ai/test_ai_config_factory.py
"""Configuration and disabled runtime tests for multi-provider AI composition."""

import unittest

from app.application.ai_login import AILoginStrategy, AIProviderName
from app.infrastructure.ai.config import load_ai_config
from app.infrastructure.ai.factory import build_ai_runtime


class AIConfigFactoryTests(unittest.TestCase):
    def test_disabled_is_zero_credential_and_zero_capability(self):
        config = load_ai_config({"AI_ENABLED": "false", "OPENAI_API_KEY": "secret"}, "playwright")
        runtime = build_ai_runtime(config)
        self.assertFalse(config.enabled)
        self.assertEqual(config.api_key, "")
        self.assertEqual(runtime.provider, AIProviderName.DISABLED)
        self.assertFalse(runtime.health.get_health().enabled)

    def test_openai_semantic_reads_only_openai_configuration(self):
        config = load_ai_config({
            "AI_ENABLED": "true", "AI_PROVIDER": "openai", "AI_LOGIN_STRATEGY": "semantic",
            "AI_MODEL": "vision-model", "OPENAI_API_KEY": "openai-secret",
            "GEMINI_API_KEY": "must-not-be-selected",
        }, "drissionpage")
        self.assertTrue(config.enabled)
        self.assertEqual(config.provider, AIProviderName.OPENAI)
        self.assertEqual(config.strategy, AILoginStrategy.SEMANTIC)
        self.assertEqual(config.api_key, "openai-secret")

    def test_non_semantic_strategy_fails_closed(self):
        unsupported = load_ai_config({
            "AI_ENABLED": "true", "AI_PROVIDER": "openai", "AI_MODEL": "m",
            "OPENAI_API_KEY": "k", "AI_LOGIN_STRATEGY": "agentic",
        }, "playwright")
        self.assertFalse(unsupported.enabled)
        self.assertIn("agentic", unsupported.error)


if __name__ == "__main__":
    unittest.main()
