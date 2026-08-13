# File: backend/tests/unit/automation/test_login_status_verification.py
"""Unified terminal assessment privacy, deduplication, and conflict-policy tests."""

import threading
import unittest

from app.application.ai_login import (
    AIFailureCode, AIProviderHealth, TerminalAssessment,
    TerminalAssessmentPort, VerificationOutcome,
)
from app.domain.models import LoginStatus, Platform
from app.infrastructure.ai.config import AILimits
from app.infrastructure.automation.ai_login_context import AILoginContextFactory
from app.infrastructure.automation.page_wrapper import AutomationPage
from app.infrastructure.automation.terminal_status_coordinator import TerminalStatusCoordinator


class FakePage(AutomationPage):
    def __init__(self, url="https://www.facebook.com/home.php", html='<main role="feed">'):
        self._url, self._html = url, html

    def goto(self, url): self._url = url
    def find(self, selector, timeout=5): return None
    def find_first(self, *selectors, timeout=5): return None
    def find_semantic(self, platform, intent, cancellation_event=None): return None
    def find_with_ai_fallback(self, selector, hint_text, timeout=5): return None
    def capture_screenshot_base64(self, mask_sensitive=True): return "ZmFrZQ=="
    @property
    def url(self): return self._url
    @property
    def html(self): return self._html


class FakeTerminal(TerminalAssessmentPort):
    provider, model = "fake", "vision"

    def __init__(self, status=LoginStatus.LOGGED_OUT, confidence=.9, failure=None):
        self.status, self.confidence, self.failure = status, confidence, failure
        self.calls, self.last = 0, None

    def assess_terminal(self, observation, preliminary_status, cancellation_event=None):
        self.calls += 1
        self.last = observation
        return TerminalAssessment(self.status, self.confidence, "safe evidence",
                                  observation.observation_id, ("visual",), ("dom",), True,
                                  self.provider, self.model, failure_code=self.failure)


class TerminalStatusCoordinatorTests(unittest.TestCase):
    def coordinator(self, port):
        context = AILoginContextFactory(AILimits()).create()
        return TerminalStatusCoordinator(port, context), context

    def test_logged_in_is_zero_call(self):
        port = FakeTerminal(LoginStatus.DEAD)
        coordinator, _ = self.coordinator(port)
        decision = coordinator.resolve(FakePage(), Platform.FACEBOOK, LoginStatus.LOGGED_IN)
        self.assertEqual(decision.outcome, VerificationOutcome.SKIPPED_LOGGED_IN)
        self.assertEqual(port.calls, 0)

    def test_checkpoint_hard_evidence_overrides_advisory_output(self):
        port = FakeTerminal(LoginStatus.LOGGED_IN, 1)
        coordinator, _ = self.coordinator(port)
        page = FakePage("https://www.facebook.com/checkpoint", "captcha challenge")
        decision = coordinator.resolve(page, Platform.FACEBOOK, LoginStatus.LOGGED_OUT)
        self.assertEqual(decision.final_status, LoginStatus.CHECKPOINT)

    def test_failure_and_low_confidence_preserve_preliminary(self):
        failed, _ = self.coordinator(FakeTerminal(None, 0, AIFailureCode.UNAVAILABLE))
        self.assertEqual(failed.resolve(
            FakePage(), Platform.FACEBOOK, LoginStatus.DEAD).final_status, LoginStatus.DEAD)
        low, _ = self.coordinator(FakeTerminal(LoginStatus.CHECKPOINT, .2))
        decision = low.resolve(FakePage(), Platform.FACEBOOK, LoginStatus.LOGGED_OUT)
        self.assertEqual((decision.final_status, decision.outcome),
                         (LoginStatus.LOGGED_OUT, VerificationOutcome.REJECTED))

    def test_protected_evidence_redacts_url_dom_and_secrets(self):
        port = FakeTerminal(LoginStatus.CHECKPOINT)
        coordinator, _ = self.coordinator(port)
        page = FakePage("https://user:pw@www.facebook.com/checkpoint?token=secret#x",
                        '<input value="secret" aria-label="user@example.com">')
        coordinator.resolve(page, Platform.FACEBOOK, LoginStatus.CHECKPOINT,
                            ("secret", "user@example.com"))
        self.assertNotIn("secret", port.last.redacted_url)
        self.assertNotIn("user@example.com", port.last.dom_snippet)
        self.assertNotIn("value=", port.last.dom_snippet)

    def test_matching_cached_assessment_is_reused_without_call(self):
        port = FakeTerminal()
        coordinator, context = self.coordinator(port)
        page = FakePage()
        first = coordinator.resolve(page, Platform.FACEBOOK, LoginStatus.LOGGED_OUT)
        self.assertEqual(port.calls, 1)
        second = coordinator.resolve(page, Platform.FACEBOOK, LoginStatus.LOGGED_OUT)
        self.assertEqual(second.outcome, VerificationOutcome.REUSED)
        self.assertEqual(port.calls, 1)


if __name__ == "__main__":
    unittest.main()
