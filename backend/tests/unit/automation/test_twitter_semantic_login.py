# File: backend/tests/unit/automation/test_twitter_semantic_login.py
"""Focused X staged semantic login tests."""

import unittest
from unittest.mock import patch

from app.domain.models import LoginStatus, Platform
from app.infrastructure.automation.platforms.twitter import login_twitter
from app.infrastructure.automation.semantic_types import (
    ResolutionFailure, ResolutionSource, SemanticIntent, SemanticResolution,
)


class FakeElement:
    def __init__(self, callback=None):
        self.callback = callback
        self.inputs, self.clicks, self.presses = [], 0, []

    def input(self, value):
        self.inputs.append(value)

    def click(self, by_js=False):
        self.clicks += 1
        if self.callback:
            self.callback()

    def press(self, key):
        self.presses.append(key)
        if self.callback:
            self.callback()


def resolved(element):
    return SemanticResolution(
        element, ResolutionSource.AI, ResolutionFailure.NONE, 1, 0.93, "resolved",
    )


def unresolved():
    return SemanticResolution(None, ResolutionSource.NONE, ResolutionFailure.NOT_FOUND)


class FakePage:
    def __init__(self):
        self.url = ""
        self.stage = "username"
        self.confirmation = False
        self.batches = []
        self.batch_results = []

    def goto(self, url):
        self.url = url

    def find_first(self, *selectors, timeout=5.0):
        if self.stage == "username" and "css:input[name='text']" in selectors:
            return object()
        if self.stage == "password" and "css:input[name='password']" in selectors:
            return object()
        return None

    def find_semantic_many(self, platform, intents, cancellation_event=None):
        self.batches.append((platform, intents))
        results = self.batch_results[len(self.batches) - 1]
        return {intent: results[intent] for intent in intents}

    def find(self, selector, timeout=5.0):
        if self.confirmation and selector == "css:input[data-testid='ocfEnterTextTextInput']":
            return object()
        return None


def run(generator):
    try:
        while True:
            next(generator)
    except StopIteration as stop:
        return stop.value


class TwitterSemanticLoginTests(unittest.TestCase):
    @patch("app.infrastructure.automation.platforms.twitter.wait_or_cancel", return_value=False)
    def test_uses_two_stage_batches(self, _wait):
        page = FakePage()
        username, password = FakeElement(), FakeElement()
        next_button = FakeElement(lambda: setattr(page, "stage", "password"))
        login_button = FakeElement(lambda: setattr(page, "url", "https://x.com/home"))
        page.batch_results = [
            {
                SemanticIntent.EMAIL_OR_PHONE_INPUT: resolved(username),
                SemanticIntent.CONTINUE_CONTROL: resolved(next_button),
            },
            {
                SemanticIntent.PASSWORD_INPUT: resolved(password),
                SemanticIntent.LOGIN_SUBMIT_CONTROL: resolved(login_button),
            },
        ]

        status = run(login_twitter(page, "user", "secret", lambda message: message))

        self.assertEqual(status, LoginStatus.LOGGED_IN)
        self.assertEqual(page.batches, [
            (Platform.TWITTER, (
                SemanticIntent.EMAIL_OR_PHONE_INPUT, SemanticIntent.CONTINUE_CONTROL,
            )),
            (Platform.TWITTER, (
                SemanticIntent.PASSWORD_INPUT, SemanticIntent.LOGIN_SUBMIT_CONTROL,
            )),
        ])
        self.assertEqual(username.inputs, ["user"])
        self.assertEqual(password.inputs, ["secret"])

    @patch("app.infrastructure.automation.platforms.twitter.wait_or_cancel", return_value=False)
    def test_identity_confirmation_stops_before_password_batch(self, _wait):
        page = FakePage()
        next_button = FakeElement(lambda: setattr(page, "confirmation", True))
        page.batch_results = [{
            SemanticIntent.EMAIL_OR_PHONE_INPUT: resolved(FakeElement()),
            SemanticIntent.CONTINUE_CONTROL: resolved(next_button),
        }]

        status = run(login_twitter(page, "user", "secret", lambda message: message))

        self.assertEqual(status, LoginStatus.CHECKPOINT)
        self.assertEqual(len(page.batches), 1)

    @patch("app.infrastructure.automation.platforms.twitter.wait_or_cancel", return_value=False)
    def test_missing_submit_uses_password_enter(self, _wait):
        page = FakePage()
        password = FakeElement(lambda: setattr(page, "url", "https://x.com/home"))
        next_button = FakeElement(lambda: setattr(page, "stage", "password"))
        page.batch_results = [
            {
                SemanticIntent.EMAIL_OR_PHONE_INPUT: resolved(FakeElement()),
                SemanticIntent.CONTINUE_CONTROL: resolved(next_button),
            },
            {
                SemanticIntent.PASSWORD_INPUT: resolved(password),
                SemanticIntent.LOGIN_SUBMIT_CONTROL: unresolved(),
            },
        ]

        status = run(login_twitter(page, "user", "secret", lambda message: message))

        self.assertEqual(status, LoginStatus.LOGGED_IN)
        self.assertEqual(password.presses, ["Enter"])


if __name__ == "__main__":
    unittest.main()
