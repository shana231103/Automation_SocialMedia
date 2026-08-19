# File: backend/tests/unit/automation/test_tiktok_semantic_login.py
"""Focused TikTok semantic batch login tests."""

import unittest
from unittest.mock import patch

from app.domain.models import LoginStatus, Platform
from app.infrastructure.automation.platforms.tiktok import login_tiktok
from app.infrastructure.automation.semantic_types import (
    ResolutionFailure, ResolutionSource, SemanticIntent, SemanticResolution,
)


class FakeElement:
    def __init__(self, on_submit=None):
        self.inputs, self.clicks, self.presses = [], 0, []
        self.on_submit = on_submit

    def input(self, value):
        self.inputs.append(value)

    def click(self, by_js=False):
        self.clicks += 1
        if self.on_submit:
            self.on_submit()

    def press(self, key):
        self.presses.append(key)
        if self.on_submit:
            self.on_submit()


def resolved(element, source=ResolutionSource.AI, attempts=1):
    return SemanticResolution(
        element, source, ResolutionFailure.NONE, attempts, 0.91, "resolved",
    )


def unresolved(failure=ResolutionFailure.NOT_FOUND):
    return SemanticResolution(None, ResolutionSource.NONE, failure)


class FakePage:
    def __init__(self, resolutions):
        self.url = ""
        self.resolutions = resolutions
        self.semantic_batch_calls = []
        self.authenticated = False

    def goto(self, url):
        self.url = url

    def find_first(self, *selectors, timeout=5.0):
        if "css:input[name='username']" in selectors:
            return object()
        return None

    def find_semantic_many(self, platform, intents, cancellation_event=None):
        self.semantic_batch_calls.append((platform, intents, cancellation_event))
        return {intent: self.resolutions[intent] for intent in intents}

    def find(self, selector, timeout=5.0):
        if self.authenticated and selector in {
            "css:[data-e2e='profile-icon']", "css:[data-e2e='profile-avatar']",
        }:
            return object()
        return None


def run(generator):
    events = []
    try:
        while True:
            events.append(next(generator))
    except StopIteration as stop:
        return stop.value, events


class TikTokSemanticLoginTests(unittest.TestCase):
    @patch("app.infrastructure.automation.platforms.tiktok.wait_or_cancel", return_value=False)
    def test_resolves_three_controls_in_one_batch(self, _wait):
        page = FakePage({})
        username, password = FakeElement(), FakeElement()
        submit = FakeElement(lambda: setattr(page, "authenticated", True))
        page.resolutions = {
            SemanticIntent.EMAIL_OR_PHONE_INPUT: resolved(username),
            SemanticIntent.PASSWORD_INPUT: resolved(password),
            SemanticIntent.LOGIN_SUBMIT_CONTROL: resolved(submit),
        }

        status, _ = run(login_tiktok(page, "user", "secret", lambda message: message))

        self.assertEqual(status, LoginStatus.LOGGED_IN)
        self.assertEqual(len(page.semantic_batch_calls), 1)
        platform, intents, _ = page.semantic_batch_calls[0]
        self.assertEqual(platform, Platform.TIKTOK)
        self.assertEqual(intents, (
            SemanticIntent.EMAIL_OR_PHONE_INPUT,
            SemanticIntent.PASSWORD_INPUT,
            SemanticIntent.LOGIN_SUBMIT_CONTROL,
        ))
        self.assertEqual(username.inputs, ["user"])
        self.assertEqual(password.inputs, ["secret"])
        self.assertEqual(submit.clicks, 1)

    @patch("app.infrastructure.automation.platforms.tiktok.wait_or_cancel", return_value=False)
    def test_missing_submit_uses_password_enter(self, _wait):
        page = FakePage({})
        username, password = FakeElement(), FakeElement(
            lambda: setattr(page, "authenticated", True)
        )
        page.resolutions = {
            SemanticIntent.EMAIL_OR_PHONE_INPUT: resolved(username),
            SemanticIntent.PASSWORD_INPUT: resolved(password),
            SemanticIntent.LOGIN_SUBMIT_CONTROL: unresolved(),
        }

        status, events = run(login_tiktok(page, "user", "secret", lambda message: message))

        self.assertEqual(status, LoginStatus.LOGGED_IN)
        self.assertEqual(password.presses, ["Enter"])
        self.assertTrue(any("submitting by keyboard" in event for event in events))


if __name__ == "__main__":
    unittest.main()
