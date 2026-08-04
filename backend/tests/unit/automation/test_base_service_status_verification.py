# File: backend/tests/unit/automation/test_base_service_status_verification.py
"""Integration-style tests for verification inside the active browser context."""

import unittest

from app.application.status_verification import (
    AccountStatusVerifier,
    StatusVerificationAssessment,
    StatusVerifierHealth,
    VerificationFailureCode,
)
from app.domain.models import LoginStatus, Platform
from app.infrastructure.automation.actions import ACTION_REGISTRY
from app.infrastructure.automation.actions.action_base import AutomationAction
from app.infrastructure.automation.base_service import BaseAutomationService
from app.infrastructure.automation.login_status_verification import LoginStatusVerificationCoordinator
from app.infrastructure.automation.page_wrapper import AutomationPage


class DummyLoginAction(AutomationAction):
    def execute(self, page, params, log_func):
        yield log_func("rule-based login classification complete")
        return params["preliminary_status"]


class FakeBrowser:
    def __init__(self):
        self.active = False

    def __enter__(self):
        self.active = True
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.active = False
        return False

    def get_new_logs(self):
        return []


class FakePage(AutomationPage):
    def __init__(self, native_page):
        self.native_page = native_page

    def goto(self, url: str) -> None:
        return None

    def find(self, selector: str, timeout: float = 5.0):
        return None

    def find_first(self, *selectors: str, timeout: float = 5.0):
        return None

    def find_with_ai_fallback(self, selector: str, hint_text: str, timeout: float = 5.0):
        return None

    def capture_screenshot_base64(self, mask_sensitive: bool = True) -> str:
        if not self.native_page.active:
            raise RuntimeError("browser context already closed")
        return "ZmFrZQ=="

    @property
    def url(self) -> str:
        return "https://www.facebook.com/checkpoint"

    @property
    def html(self) -> str:
        return '<main role="main"><div aria-label="challenge">'


class FakeVerifier(AccountStatusVerifier):
    provider, model = "ollama", "qwen3.5:9b"

    def __init__(self, result):
        self.result = result
        self.calls = 0

    def verify(self, evidence, cancellation_event=None):
        self.calls += 1
        return self.result

    def get_status(self):
        return StatusVerifierHealth(True, self.provider, self.model, True, True, True, "ready")


def ai_result(status, confidence=0.9, failure_code=None):
    return StatusVerificationAssessment(
        status=status,
        confidence=confidence,
        reasoning="challenge evidence",
        visual_evidence=("challenge",),
        dom_evidence=("challenge",),
        model_agreement=False,
        failure_code=failure_code,
        provider="ollama",
        model="qwen3.5:9b",
    )


class BaseServiceVerificationTests(unittest.TestCase):
    def setUp(self):
        self.original_login_action = ACTION_REGISTRY["login"]
        ACTION_REGISTRY["login"] = DummyLoginAction

    def tearDown(self):
        ACTION_REGISTRY["login"] = self.original_login_action

    def run_service(self, preliminary, verifier):
        browser = FakeBrowser()
        coordinator = LoginStatusVerificationCoordinator(verifier)
        service = BaseAutomationService(lambda key, name=None: browser, FakePage, coordinator)
        events = list(service.run_action(
            "login",
            {
                "username": "user", "password": "password",
                "platform": Platform.FACEBOOK, "preliminary_status": preliminary,
                "cancellation_event": None,
            },
            "profile",
        ))
        return browser, events

    def test_logged_in_skips_verifier_and_emits_one_result(self):
        verifier = FakeVerifier(ai_result(LoginStatus.DEAD))
        browser, events = self.run_service(LoginStatus.LOGGED_IN, verifier)
        results = [event for event in events if event["type"] == "result"]
        self.assertEqual(verifier.calls, 0)
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["status"], LoginStatus.LOGGED_IN)
        self.assertNotIn("verification", results[0])
        self.assertFalse(browser.active)

    def test_non_success_verifies_before_context_exit_and_overrides(self):
        verifier = FakeVerifier(ai_result(LoginStatus.CHECKPOINT))
        browser, events = self.run_service(LoginStatus.DEAD, verifier)
        results = [event for event in events if event["type"] == "result"]
        self.assertEqual(verifier.calls, 1)
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["status"], LoginStatus.CHECKPOINT)
        self.assertEqual(results[0]["verification"]["outcome"], "overridden")
        self.assertEqual(results[0]["verification"]["visual_evidence"], ["challenge"])
        explanation = next(
            event["message"] for event in events
            if event["type"] == "log" and "AI status verification" in event["message"]
        )
        self.assertIn("Lý do: challenge evidence", explanation)
        self.assertIn("Thấy trên ảnh: challenge", explanation)
        self.assertIn("Thấy trong DOM: challenge", explanation)
        self.assertNotIn("screenshot_base64", results[0]["verification"])
        self.assertFalse(browser.active)

    def test_verifier_failure_preserves_preliminary_status(self):
        verifier = FakeVerifier(ai_result(None, 0.0, VerificationFailureCode.UNAVAILABLE))
        _, events = self.run_service(LoginStatus.CHECKPOINT, verifier)
        result = next(event for event in events if event["type"] == "result")
        self.assertEqual(result["status"], LoginStatus.CHECKPOINT)
        self.assertEqual(result["verification"]["outcome"], "fallback")
        self.assertEqual(result["verification"]["failure_code"], "unavailable")
        explanation = next(
            event["message"] for event in events
            if event["type"] == "log" and "AI status verification" in event["message"]
        )
        self.assertIn("Mã lỗi: unavailable", explanation)


if __name__ == "__main__":
    unittest.main()
