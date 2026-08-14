"""Focused Facebook tests for semantic resolution and submit behavior."""

import unittest
from unittest.mock import patch

from app.domain.models import LoginStatus, Platform
from app.infrastructure.automation.platforms.facebook import login_facebook
from app.infrastructure.automation.semantic_types import (
    ResolutionFailure, ResolutionSource, SemanticIntent, SemanticResolution,
)


class FakeElement:
    def __init__(self, on_submit=None):
        self.inputs = []
        self.clicks = []
        self.presses = []
        self.on_submit = on_submit

    def input(self, text):
        self.inputs.append(text)

    def click(self, by_js=False):
        self.clicks.append(by_js)
        if self.on_submit:
            self.on_submit()

    def press(self, key):
        self.presses.append(key)
        if self.on_submit:
            self.on_submit()

    def exists(self):
        return True


class FakePage:
    def __init__(self, resolutions):
        self._url = "https://www.facebook.com/"
        self.resolutions = resolutions
        self.semantic_calls = []
        self.semantic_batch_calls = []

    def goto(self, url):
        self._url = url

    def find(self, selector, timeout=5.0):
        return None

    def find_semantic(self, platform, intent, cancellation_event=None):
        self.semantic_calls.append((platform, intent, cancellation_event))
        return self.resolutions[intent]

    def find_semantic_many(self, platform, intents, cancellation_event=None):
        self.semantic_batch_calls.append((platform, intents, cancellation_event))
        return {intent: self.resolutions[intent] for intent in intents}

    @property
    def url(self):
        return self._url


def resolved(element, source=ResolutionSource.AI, attempts=1):
    return SemanticResolution(
        element, source, ResolutionFailure.NONE, attempts, 0.9, "resolved",
    )


def unresolved(failure=ResolutionFailure.NOT_FOUND):
    return SemanticResolution(None, ResolutionSource.NONE, failure)


def run(generator):
    events = []
    try:
        while True:
            events.append(next(generator))
    except StopIteration as stop:
        return stop.value, events


def log(message):
    return {"type": "log", "message": message}


class FacebookSemanticLoginTests(unittest.TestCase):
    def setUp(self):
        self.wait_patch = patch(
            "app.infrastructure.automation.platforms.facebook._cancelled",
            side_effect=lambda event, seconds: bool(event and event.is_set()),
        )
        self.wait_patch.start()
        self.addCleanup(self.wait_patch.stop)

    def test_success_uses_semantic_intents_and_clicks_submit(self):
        email, password = FakeElement(), FakeElement()
        page = FakePage({})
        submit = FakeElement(lambda: setattr(page, "_url", "https://www.facebook.com/home.php"))
        page.resolutions = {
            SemanticIntent.EMAIL_OR_PHONE_INPUT: resolved(email),
            SemanticIntent.PASSWORD_INPUT: resolved(password, ResolutionSource.REGISTRY, 2),
            SemanticIntent.LOGIN_SUBMIT_CONTROL: resolved(submit),
        }
        status, _ = run(login_facebook(page, "user", "secret", log))
        self.assertEqual(status, LoginStatus.LOGGED_IN)
        self.assertEqual(email.inputs, ["user"])
        self.assertEqual(password.inputs, ["secret"])
        self.assertEqual(submit.clicks, [False])
        self.assertFalse(page.semantic_calls)
        self.assertEqual(len(page.semantic_batch_calls), 1)
        self.assertEqual(page.semantic_batch_calls[0][0], Platform.FACEBOOK)
        self.assertEqual(page.semantic_batch_calls[0][1], (
            SemanticIntent.EMAIL_OR_PHONE_INPUT, SemanticIntent.PASSWORD_INPUT,
            SemanticIntent.LOGIN_SUBMIT_CONTROL,
        ))

    def test_unresolved_credentials_stop_before_input(self):
        email = FakeElement()
        page = FakePage({
            SemanticIntent.EMAIL_OR_PHONE_INPUT: resolved(email),
            SemanticIntent.PASSWORD_INPUT: unresolved(),
            SemanticIntent.LOGIN_SUBMIT_CONTROL: unresolved(),
        })
        status, events = run(login_facebook(page, "user", "secret", log))
        self.assertEqual(status, LoginStatus.LOGGED_OUT)
        self.assertFalse(email.inputs)
        self.assertIn("manual intervention", events[-1]["message"])

    def test_unresolved_submit_falls_back_to_enter(self):
        page = FakePage({})
        password = FakeElement(lambda: setattr(page, "_url", "https://www.facebook.com/home.php"))
        page.resolutions = {
            SemanticIntent.EMAIL_OR_PHONE_INPUT: resolved(FakeElement()),
            SemanticIntent.PASSWORD_INPUT: resolved(password),
            SemanticIntent.LOGIN_SUBMIT_CONTROL: unresolved(),
        }
        status, events = run(login_facebook(page, "user", "secret", log))
        self.assertEqual(status, LoginStatus.LOGGED_IN)
        self.assertEqual(password.presses, ["Enter"])
        self.assertTrue(any("submitting by keyboard" in event["message"] for event in events))

    def test_cancelled_resolution_stops_without_fallback(self):
        page = FakePage({SemanticIntent.EMAIL_OR_PHONE_INPUT: unresolved(
            ResolutionFailure.CANCELLED,
        ), SemanticIntent.PASSWORD_INPUT: unresolved(),
            SemanticIntent.LOGIN_SUBMIT_CONTROL: unresolved()})
        status, events = run(login_facebook(page, "user", "secret", log))
        self.assertEqual(status, LoginStatus.LOGGED_OUT)
        self.assertEqual(len(page.semantic_batch_calls), 1)
        self.assertIn("cancelled", events[-1]["message"])


if __name__ == "__main__":
    unittest.main()
