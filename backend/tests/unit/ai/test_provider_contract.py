# File: backend/tests/unit/ai/test_provider_contract.py
"""Shared normalized provider-port contract tests."""

import threading
import unittest

from app.application.ai_login import (
    AIFailureCode, ProtectedObservation, SelectorAssessment, SelectorBatchAssessment,
    TerminalAssessment,
)
from app.domain.models import LoginStatus, Platform


class ContractProvider:
    def predict_selector(self, observation, intent, cancellation_event=None):
        if cancellation_event and cancellation_event.is_set():
            return SelectorAssessment(failure_code=AIFailureCode.CANCELLED)
        return SelectorAssessment("css:#login", .9, "visible", "fake", "m")

    def predict_selectors(self, observation, intents, cancellation_event=None):
        items = tuple((intent, self.predict_selector(
            observation, intent, cancellation_event,
        )) for intent in intents)
        return SelectorBatchAssessment(items)

    def assess_terminal(self, observation, preliminary_status, cancellation_event=None):
        if cancellation_event and cancellation_event.is_set():
            return TerminalAssessment(None, 0, "cancelled", observation.observation_id,
                                      failure_code=AIFailureCode.CANCELLED)
        return TerminalAssessment(preliminary_status, .9, "confirmed",
                                  observation.observation_id, provider="fake", model="m")


class ProviderContractTests(unittest.TestCase):
    def setUp(self):
        self.observation = ProtectedObservation("o", Platform.FACEBOOK,
                                                "https://www.facebook.com", "aW1n",
                                                "<main>")

    def test_success_values_are_normalized_and_bound_to_observation(self):
        provider = ContractProvider()
        selector = provider.predict_selector(self.observation, "login")
        batch = provider.predict_selectors(self.observation, ("email", "password", "submit"))
        terminal = provider.assess_terminal(self.observation, LoginStatus.LOGGED_OUT)
        self.assertEqual(selector.selector, "css:#login")
        self.assertEqual(terminal.observation_id, self.observation.observation_id)
        self.assertIsNone(selector.failure_code)
        self.assertEqual(tuple(batch.by_intent()), ("email", "password", "submit"))

    def test_cancellation_is_typed_and_never_raises_sdk_errors(self):
        event = threading.Event()
        event.set()
        provider = ContractProvider()
        self.assertEqual(provider.predict_selector(
            self.observation, "login", event).failure_code, AIFailureCode.CANCELLED)
        self.assertTrue(all(item.failure_code == AIFailureCode.CANCELLED
                            for item in provider.predict_selectors(
                                self.observation, ("email", "password"), event,
                            ).by_intent().values()))
        self.assertEqual(provider.assess_terminal(
            self.observation, LoginStatus.LOGGED_OUT, event).failure_code,
            AIFailureCode.CANCELLED)


if __name__ == "__main__":
    unittest.main()
