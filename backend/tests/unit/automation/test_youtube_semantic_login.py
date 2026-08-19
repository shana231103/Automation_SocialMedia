# File: backend/tests/unit/automation/test_youtube_semantic_login.py
"""Focused Google/YouTube staged semantic login tests."""

import unittest
from unittest.mock import patch

from app.domain.models import LoginStatus, Platform
from app.infrastructure.automation.platforms.youtube import login_youtube
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
        element, ResolutionSource.AI, ResolutionFailure.NONE, 1, 0.92, "resolved",
    )


def unresolved():
    return SemanticResolution(None, ResolutionSource.NONE, ResolutionFailure.NOT_FOUND)


class FakePage:
    def __init__(self):
        self.url = ""
        self.stage = "identifier"
        self.batches = []
        self.batch_results = []
        self.account_error = False

    def goto(self, url):
        self.url = url

    def find_first(self, *selectors, timeout=5.0):
        if self.stage == "identifier" and (
            "css:input[type='email']" in selectors or "#identifierId" in selectors
        ):
            return object()
        if self.stage == "password" and "css:input[type='password']" in selectors:
            return object()
        return None

    def find_semantic_many(self, platform, intents, cancellation_event=None):
        self.batches.append((platform, intents))
        results = self.batch_results[len(self.batches) - 1]
        return {intent: results[intent] for intent in intents}

    def find(self, selector, timeout=5.0):
        if self.account_error and selector == "text:Couldn't find your Google Account":
            return object()
        return None


def run(generator):
    try:
        while True:
            next(generator)
    except StopIteration as stop:
        return stop.value


class YouTubeSemanticLoginTests(unittest.TestCase):
    @patch("app.infrastructure.automation.platforms.youtube.wait_or_cancel", return_value=False)
    def test_uses_separate_identifier_and_password_batches(self, _wait):
        page = FakePage()
        email, password = FakeElement(), FakeElement()
        identifier_next = FakeElement(lambda: setattr(page, "stage", "password"))
        password_next = FakeElement(lambda: setattr(page, "url", "https://www.youtube.com/"))
        page.batch_results = [
            {
                SemanticIntent.EMAIL_OR_PHONE_INPUT: resolved(email),
                SemanticIntent.CONTINUE_CONTROL: resolved(identifier_next),
            },
            {
                SemanticIntent.PASSWORD_INPUT: resolved(password),
                SemanticIntent.LOGIN_SUBMIT_CONTROL: resolved(password_next),
            },
        ]

        status = run(login_youtube(page, "user", "secret", lambda message: message))

        self.assertEqual(status, LoginStatus.LOGGED_IN)
        self.assertEqual(page.batches, [
            (Platform.YOUTUBE, (
                SemanticIntent.EMAIL_OR_PHONE_INPUT, SemanticIntent.CONTINUE_CONTROL,
            )),
            (Platform.YOUTUBE, (
                SemanticIntent.PASSWORD_INPUT, SemanticIntent.LOGIN_SUBMIT_CONTROL,
            )),
        ])
        self.assertEqual(email.inputs, ["user"])
        self.assertEqual(password.inputs, ["secret"])

    @patch("app.infrastructure.automation.platforms.youtube.wait_or_cancel", return_value=False)
    def test_account_error_stops_before_password_batch(self, _wait):
        page = FakePage()
        email = FakeElement()
        next_button = FakeElement(lambda: setattr(page, "account_error", True))
        page.batch_results = [{
            SemanticIntent.EMAIL_OR_PHONE_INPUT: resolved(email),
            SemanticIntent.CONTINUE_CONTROL: resolved(next_button),
        }]

        status = run(login_youtube(page, "missing", "secret", lambda message: message))

        self.assertEqual(status, LoginStatus.LOGGED_OUT)
        self.assertEqual(len(page.batches), 1)

    @patch("app.infrastructure.automation.platforms.youtube.wait_or_cancel", return_value=False)
    def test_missing_password_remains_checkpoint(self, _wait):
        page = FakePage()
        next_button = FakeElement(lambda: setattr(page, "stage", "password"))
        page.batch_results = [
            {
                SemanticIntent.EMAIL_OR_PHONE_INPUT: resolved(FakeElement()),
                SemanticIntent.CONTINUE_CONTROL: resolved(next_button),
            },
            {
                SemanticIntent.PASSWORD_INPUT: unresolved(),
                SemanticIntent.LOGIN_SUBMIT_CONTROL: unresolved(),
            },
        ]

        status = run(login_youtube(page, "user", "secret", lambda message: message))

        self.assertEqual(status, LoginStatus.CHECKPOINT)
        self.assertEqual(len(page.batches), 2)


if __name__ == "__main__":
    unittest.main()
