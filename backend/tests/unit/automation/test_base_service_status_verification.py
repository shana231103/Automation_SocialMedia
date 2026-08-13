# File: backend/tests/unit/automation/test_base_service_status_verification.py
"""Unified AI orchestration stays inside the live browser context."""

import unittest

from app.application.ai_login import (
    AILoginRuntime, AILoginStrategy, AIProviderHealth, AIProviderName,
    TerminalAssessment, TerminalAssessmentPort,
)
from app.domain.models import LoginStatus, Platform
from app.infrastructure.ai.config import AILimits
from app.infrastructure.ai.factory import DisabledAIHealth
from app.infrastructure.automation.actions import ACTION_REGISTRY
from app.infrastructure.automation.actions.action_base import AutomationAction
from app.infrastructure.automation.ai_login_context import AILoginContextFactory
from app.infrastructure.automation.base_service import BaseAutomationService
from app.infrastructure.automation.page_wrapper import AutomationPage


class DummyLoginAction(AutomationAction):
    def execute(self, page, params, log_func):
        yield log_func("deterministic classification complete")
        return params["preliminary_status"]


class FakeBrowser:
    def __init__(self): self.active = False
    def __enter__(self): self.active = True; return self
    def __exit__(self, *args): self.active = False; return False
    def get_new_logs(self): return []


class FakePage(AutomationPage):
    def __init__(self, native, resolver=None): self.native = native
    def goto(self, url): return None
    def find(self, selector, timeout=5): return None
    def find_first(self, *selectors, timeout=5): return None
    def find_semantic(self, platform, intent, cancellation_event=None): return None
    def find_with_ai_fallback(self, selector, hint_text, timeout=5): return None
    def capture_screenshot_base64(self, mask_sensitive=True):
        if not self.native.active: raise RuntimeError("closed")
        return "ZmFrZQ=="
    @property
    def url(self): return "https://www.facebook.com/checkpoint"
    @property
    def html(self): return '<main><div aria-label="challenge">'
class FakeTerminal(TerminalAssessmentPort):
    def __init__(self): self.calls = 0
    def assess_terminal(self, observation, preliminary_status, cancellation_event=None):
        self.calls += 1
        return TerminalAssessment(LoginStatus.CHECKPOINT, .9, "challenge",
                                  observation.observation_id, ("challenge",), ("challenge",),
                                  False, "fake", "vision")


class BaseServiceTests(unittest.TestCase):
    def setUp(self):
        self.original = ACTION_REGISTRY["login"]
        ACTION_REGISTRY["login"] = DummyLoginAction

    def tearDown(self): ACTION_REGISTRY["login"] = self.original

    def service(self, terminal=None):
        browser = FakeBrowser()
        limits = AILimits()
        runtime = AILoginRuntime(None, terminal, DisabledAIHealth(),
                                 AIProviderName.DISABLED, AILoginStrategy.DISABLED)
        return browser, BaseAutomationService(
            lambda key, name=None: browser, FakePage, runtime,
            AILoginContextFactory(limits))

    def run(self, preliminary, terminal=None):
        browser, service = self.service(terminal)
        events = list(service.run_action("login", {
            "username": "user", "password": "password", "platform": Platform.FACEBOOK,
            "preliminary_status": preliminary, "cancellation_event": None}, "profile"))
        return browser, events

    def test_logged_in_is_zero_call_and_exactly_one_result(self):
        terminal = FakeTerminal()
        browser, events = self.run(LoginStatus.LOGGED_IN, terminal)
        self.assertEqual(terminal.calls, 0)
        self.assertEqual(len([e for e in events if e["type"] == "result"]), 1)
        self.assertFalse(browser.active)

    def test_non_success_is_assessed_before_browser_exit(self):
        terminal = FakeTerminal()
        browser, events = self.run(LoginStatus.DEAD, terminal)
        result = next(e for e in events if e["type"] == "result")
        self.assertEqual(terminal.calls, 1)
        self.assertEqual(result["status"], LoginStatus.CHECKPOINT)
        self.assertEqual(result["verification"]["provider"], "fake")
        self.assertFalse(browser.active)


if __name__ == "__main__":
    unittest.main()
