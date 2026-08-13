# File: backend/tests/unit/ai/test_gemini_provider.py
"""Gemini structured adapter tests with fake SDK objects."""

import json
from types import SimpleNamespace
import unittest

from app.application.ai_login import ProtectedObservation
from app.domain.models import LoginStatus, Platform
from app.infrastructure.ai.gemini_provider import GeminiProvider


class FakeModels:
    def generate_content(self, **kwargs):
        properties = kwargs["config"]["response_json_schema"]["properties"]
        if "selector" in properties:
            payload = {"selector": "css:#login", "confidence": .9, "reasoning": "visible"}
        else:
            payload = {"status": "logged_out", "confidence": .8, "reasoning": "login form",
                       "agreement": True, "visual_evidence": ["form"], "dom_evidence": ["input"]}
        usage = SimpleNamespace(prompt_token_count=9, candidates_token_count=3, total_token_count=12)
        return SimpleNamespace(text=json.dumps(payload), usage_metadata=usage)


class GeminiProviderTests(unittest.TestCase):
    def setUp(self):
        client = SimpleNamespace(models=FakeModels())
        self.provider = GeminiProvider("key", "selector", "status", client=client)
        self.observation = ProtectedObservation("o", Platform.FACEBOOK,
                                                "https://www.facebook.com", "aW1n", "<main>")

    def test_structured_selector_and_terminal(self):
        selector = self.provider.predict_selector(self.observation, "login")
        terminal = self.provider.assess_terminal(self.observation, LoginStatus.LOGGED_OUT)
        self.assertEqual(selector.selector, "css:#login")
        self.assertEqual(terminal.status, LoginStatus.LOGGED_OUT)
        self.assertEqual(selector.usage.total_tokens, 12)

    def test_health_advertises_structured_capabilities_without_network_call(self):
        health = self.provider.get_health()
        self.assertEqual(health.capabilities, ("selector", "terminal_assessment"))
        self.assertEqual(health.strategy, "semantic")


if __name__ == "__main__":
    unittest.main()
