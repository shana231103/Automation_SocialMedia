# File: backend/tests/unit/automation/test_login_status_verification.py
"""Unit tests for verification gating, privacy, and conflict resolution."""

import threading
import unittest

from app.application.status_verification import (
    AccountStatusVerifier,
    StatusVerificationAssessment,
    StatusVerificationEvidence,
    StatusVerifierHealth,
    VerificationFailureCode,
    VerificationOutcome,
)
from app.domain.models import LoginStatus, Platform
from app.infrastructure.automation.login_status_verification import LoginStatusVerificationCoordinator
from app.infrastructure.automation.login_status_reporting import (
    decision_to_event_metadata, decision_to_log_message,
)
from app.infrastructure.automation.page_wrapper import AutomationPage
from app.infrastructure.automation.semantic_types import (
    ResolutionFailure, ResolutionSource, SemanticResolution,
)


class FakePage(AutomationPage):
    def __init__(self, url: str = "https://www.facebook.com/home.php", html: str = '<main role="feed">'):
        self._url, self._html = url, html

    def goto(self, url: str) -> None:
        self._url = url

    def find(self, selector: str, timeout: float = 5.0):
        return None

    def find_first(self, *selectors: str, timeout: float = 5.0):
        return None

    def find_semantic(self, platform, intent, cancellation_event=None):
        return SemanticResolution(
            None, ResolutionSource.NONE, ResolutionFailure.NOT_FOUND,
        )

    def find_with_ai_fallback(self, selector: str, hint_text: str, timeout: float = 5.0):
        return None

    def capture_screenshot_base64(self, mask_sensitive: bool = True) -> str:
        return "ZmFrZQ=="

    @property
    def url(self) -> str:
        return self._url

    @property
    def html(self) -> str:
        return self._html


class FakeVerifier(AccountStatusVerifier):
    provider, model = "ollama", "qwen3.5:9b"

    def __init__(self, assessment_factory):
        self.assessment_factory = assessment_factory
        self.calls = 0
        self.last_evidence = None

    def verify(self, evidence: StatusVerificationEvidence, cancellation_event=None):
        self.calls += 1
        self.last_evidence = evidence
        return self.assessment_factory(evidence)

    def get_status(self) -> StatusVerifierHealth:
        return StatusVerifierHealth(True, self.provider, self.model, True, True, True, "ready")


def assessment(status: LoginStatus | None, confidence: float = 0.9, **kwargs):
    return StatusVerificationAssessment(
        status=status,
        confidence=confidence,
        reasoning=kwargs.get("reasoning", "safe evidence"),
        visual_evidence=kwargs.get("visual_evidence", ("visual",)),
        dom_evidence=kwargs.get("dom_evidence", ("dom",)),
        model_agreement=kwargs.get("model_agreement", True),
        failure_code=kwargs.get("failure_code"),
        provider="ollama",
        model="qwen3.5:9b",
    )


class LoginStatusVerificationTests(unittest.TestCase):
    def coordinator(self, factory, **kwargs):
        verifier = FakeVerifier(factory)
        return LoginStatusVerificationCoordinator(verifier, **kwargs), verifier

    def test_logged_in_is_skipped_and_each_non_success_is_called_once(self):
        coordinator, verifier = self.coordinator(lambda evidence: assessment(evidence.preliminary_status))
        self.assertFalse(coordinator.should_verify(LoginStatus.LOGGED_IN, None))

        for status in (LoginStatus.LOGGED_OUT, LoginStatus.CHECKPOINT, LoginStatus.DEAD):
            self.assertTrue(coordinator.should_verify(status, None))
            decision = coordinator.resolve(FakePage(), Platform.FACEBOOK, status)
            self.assertEqual(decision.final_status, status)
        self.assertEqual(verifier.calls, 3)

    def test_low_confidence_is_rejected_and_non_success_override_is_allowed(self):
        low, _ = self.coordinator(lambda _: assessment(LoginStatus.DEAD, 0.79))
        self.assertEqual(
            low.resolve(FakePage(), Platform.FACEBOOK, LoginStatus.LOGGED_OUT).outcome,
            VerificationOutcome.REJECTED,
        )

        high, _ = self.coordinator(lambda _: assessment(LoginStatus.CHECKPOINT, 0.80))
        decision = high.resolve(FakePage(), Platform.FACEBOOK, LoginStatus.DEAD)
        self.assertEqual(decision.outcome, VerificationOutcome.OVERRIDDEN)
        self.assertEqual(decision.final_status, LoginStatus.CHECKPOINT)

    def test_dead_and_checkpoint_cannot_upgrade_to_logged_in(self):
        coordinator, _ = self.coordinator(lambda _: assessment(LoginStatus.LOGGED_IN, 1.0))
        for preliminary in (LoginStatus.DEAD, LoginStatus.CHECKPOINT):
            decision = coordinator.resolve(FakePage(), Platform.FACEBOOK, preliminary)
            self.assertEqual(decision.final_status, preliminary)
            self.assertEqual(decision.outcome, VerificationOutcome.REJECTED)

    def test_logged_out_can_upgrade_only_with_all_guards(self):
        coordinator, _ = self.coordinator(lambda _: assessment(LoginStatus.LOGGED_IN, 0.95))
        allowed = coordinator.resolve(FakePage(), Platform.FACEBOOK, LoginStatus.LOGGED_OUT)
        self.assertEqual(allowed.final_status, LoginStatus.LOGGED_IN)

        blocked_page = FakePage(url="https://www.facebook.com/login", html='<main role="feed">')
        blocked = coordinator.resolve(blocked_page, Platform.FACEBOOK, LoginStatus.LOGGED_OUT)
        self.assertEqual(blocked.final_status, LoginStatus.LOGGED_OUT)

    def test_url_and_dom_secrets_are_redacted_before_verifier(self):
        failure = lambda _: assessment(
            None, 0.0, failure_code=VerificationFailureCode.UNAVAILABLE,
        )
        coordinator, verifier = self.coordinator(failure)
        page = FakePage(
            url="https://user:password@www.facebook.com/checkpoint?token=secret#private",
            html='<div aria-label="user@example.com"><input value="secret">',
        )
        coordinator.resolve(
            page, Platform.FACEBOOK, LoginStatus.CHECKPOINT,
            secrets=("user@example.com", "secret"),
        )
        self.assertNotIn("secret", verifier.last_evidence.sanitized_url)
        self.assertNotIn("private", verifier.last_evidence.sanitized_url)
        self.assertNotIn("password", verifier.last_evidence.sanitized_url)
        self.assertNotIn("user@", verifier.last_evidence.sanitized_url)
        self.assertNotIn("user@example.com", verifier.last_evidence.dom_snippet)
        self.assertNotIn("value=", verifier.last_evidence.dom_snippet)
    def test_explanation_reports_safe_reason_and_observations(self):
        coordinator, _ = self.coordinator(lambda _: assessment(
            LoginStatus.CHECKPOINT,
            reasoning="captcha panel contains account-secret",
            visual_evidence=("visible CAPTCHA for account-secret",),
            dom_evidence=("checkpoint form account-secret",),
        ))
        decision = coordinator.resolve(
            FakePage(), Platform.FACEBOOK, LoginStatus.LOGGED_OUT,
            secrets=("account-secret",),
        )
        metadata = decision_to_event_metadata(decision)
        message = decision_to_log_message(decision)

        self.assertEqual(metadata["ai_status"], LoginStatus.CHECKPOINT.value)
        self.assertEqual(metadata["visual_evidence"], ["visible CAPTCHA for [redacted]"])
        self.assertIn("AI dự đoán: checkpoint", message)
        self.assertIn("Độ tin cậy: 90%", message)
        self.assertIn("Thấy trên ảnh: visible CAPTCHA for [redacted]", message)
        self.assertIn("Thấy trong DOM: checkpoint form [redacted]", message)
        self.assertNotIn("account-secret", message)

    def test_cancellation_and_disabled_configuration_do_not_call_verifier(self):
        coordinator, verifier = self.coordinator(lambda _: assessment(LoginStatus.DEAD))
        cancellation = threading.Event()
        cancellation.set()
        self.assertFalse(coordinator.should_verify(LoginStatus.LOGGED_OUT, cancellation))
        decision = coordinator.resolve(FakePage(), Platform.FACEBOOK, LoginStatus.LOGGED_OUT, cancellation_event=cancellation)
        self.assertEqual(decision.outcome, VerificationOutcome.CANCELLED)
        self.assertEqual(verifier.calls, 0)

        disabled = LoginStatusVerificationCoordinator(verifier, enabled=False, disabled_reason="disabled")
        health = disabled.get_status()
        self.assertFalse(health.enabled)
        self.assertEqual(verifier.calls, 0)


if __name__ == "__main__":
    unittest.main()
