# File: backend/tests/unit/ai/test_openai_provider.py
"""OpenAI Responses structured adapter tests with an injected fake client."""

from types import SimpleNamespace
import unittest

from app.application.ai_login import ProtectedObservation
from app.domain.models import LoginStatus, Platform
from app.infrastructure.ai.openai_provider import OpenAIProvider


class FakeResponses:
    def __init__(self):
        self.calls = []

    def parse(self, **kwargs):
        self.calls.append(kwargs)
        schema = kwargs["text_format"]
        if schema.__name__ == "OpenAISelectorBatchWire":
            parsed = schema(selectors=[
                {"intent": intent, "selector": f"css:#{index}", "confidence": .91,
                 "reasoning": "visible"}
                for index, intent in enumerate((
                    "email_or_phone_input", "password_input", "login_submit_control",
                ))
            ])
        elif "Selector" in schema.__name__:
            parsed = schema(selector="css:#login", confidence=.91, reasoning="visible")
        else:
            parsed = schema(status="checkpoint", confidence=.92, reasoning="challenge",
                            agreement=True, visual_evidence=["panel"], dom_evidence=["form"])
        content = SimpleNamespace(parsed=parsed)
        usage = SimpleNamespace(input_tokens=10, output_tokens=4, total_tokens=14)
        return SimpleNamespace(output=[SimpleNamespace(content=[content])], usage=usage)


class OpenAIProviderTests(unittest.TestCase):
    def setUp(self):
        self.responses = FakeResponses()
        client = SimpleNamespace(responses=self.responses)
        self.provider = OpenAIProvider("key", "selector", "status", client=client)
        self.observation = ProtectedObservation("o", Platform.FACEBOOK,
                                                "https://www.facebook.com/checkpoint", "aW1n",
                                                "challenge form")

    def test_selector_uses_image_input_and_structured_parse(self):
        result = self.provider.predict_selector(self.observation, "login button")
        self.assertEqual(result.selector, "css:#login")
        self.assertEqual(result.usage.total_tokens, 14)
        payload = self.responses.calls[0]
        self.assertEqual(payload["model"], "selector")
        self.assertTrue(payload["input"][0]["content"][1]["image_url"].startswith("data:image/png"))

    def test_batch_selector_uses_one_structured_parse(self):
        intents = ("email_or_phone_input", "password_input", "login_submit_control")
        result = self.provider.predict_selectors(self.observation, intents)
        self.assertEqual(tuple(result.by_intent()), intents)
        self.assertEqual(len(self.responses.calls), 1)
        self.assertEqual(result.usage.total_tokens, 14)

    def test_terminal_is_advisory_and_observation_bound(self):
        result = self.provider.assess_terminal(self.observation, LoginStatus.LOGGED_OUT)
        self.assertEqual(result.status, LoginStatus.CHECKPOINT)
        self.assertEqual(result.observation_id, "o")
        self.assertEqual(result.visual_evidence, ("panel",))

    def test_health_is_lightweight(self):
        health = self.provider.get_health()
        self.assertIsNone(health.reachable)
        self.assertEqual(len(self.responses.calls), 0)


if __name__ == "__main__":
    unittest.main()
