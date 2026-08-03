"""Regression tests for platform login status classification."""

from __future__ import annotations

import threading
import unittest
from unittest.mock import patch

from app.domain.models import LoginStatus
from app.infrastructure.automation.page_wrapper import AutomationElement, AutomationPage
from app.infrastructure.automation.platforms.facebook import login_facebook
from app.infrastructure.automation.platforms.tiktok import login_tiktok
from app.infrastructure.automation.platforms.twitter import login_twitter
from app.infrastructure.automation.platforms.youtube import login_youtube


class FakeElement(AutomationElement):
    def input(self, text: str) -> None:
        self.value = text

    def click(self, by_js: bool = False) -> None:
        self.clicked = True

    def press(self, key: str) -> None:
        self.pressed = key

    def exists(self) -> bool:
        return True


class FakePage(AutomationPage):
    def __init__(self, url_after_goto: str):
        self._url = ""
        self._html = ""
        self.url_after_goto = url_after_goto
        self.elements: dict[str, AutomationElement] = {}

    def goto(self, url: str) -> None:
        self._url = self.url_after_goto

    def find(self, selector: str, timeout: float = 5.0) -> AutomationElement | None:
        return self.elements.get(selector)

    def find_first(self, *selectors: str, timeout: float = 5.0) -> AutomationElement | None:
        return next((self.elements[selector] for selector in selectors if selector in self.elements), None)

    def find_with_ai_fallback(self, selector: str, hint_text: str, timeout: float = 5.0) -> AutomationElement | None:
        return self.find(selector, timeout)

    @property
    def url(self) -> str:
        return self._url

    @property
    def html(self) -> str:
        return self._html


def finish(generator):
    try:
        while True:
            next(generator)
    except StopIteration as stop:
        return stop.value


def log(message: str) -> dict[str, str]:
    return {"type": "log", "message": message}


class TestPlatformStatusDetection(unittest.TestCase):
    def setUp(self) -> None:
        self.sleep_patch = patch(
            "app.infrastructure.automation.platforms._helpers.time.sleep",
            return_value=None,
        )
        self.sleep_patch.start()
        self.addCleanup(self.sleep_patch.stop)

    def test_facebook_captcha_is_checkpoint_not_dead(self):
        page = FakePage("https://www.facebook.com/")
        page._html = "locked"
        page.elements.update({
            "css:input[name='email']": FakeElement(),
            "css:input[name='pass']": FakeElement(),
            "css:button[name='login']": FakeElement(),
            "css:[id*='captcha']": FakeElement(),
        })
        self.assertEqual(finish(login_facebook(page, "user", "password", log)), LoginStatus.CHECKPOINT)

    def test_tiktok_foryou_url_without_profile_is_not_authenticated(self):
        page = FakePage("https://www.tiktok.com/foryou")
        page.elements.update({
            "css:input[name='username']": FakeElement(),
            "css:input[type='password']": FakeElement(),
            "css:button[type='submit']": FakeElement(),
        })
        self.assertEqual(finish(login_tiktok(page, "user", "password", log)), LoginStatus.LOGGED_OUT)

    def test_x_redirect_query_containing_home_is_not_authenticated(self):
        page = FakePage("https://x.com/i/flow/login?redirect_after_login=%2Fhome")
        page.elements.update({
            "css:input[name='text']": FakeElement(),
            "css:input[name='password']": FakeElement(),
            "css:button[data-testid='ocfEnterTextNextButton']": FakeElement(),
            "css:button[data-testid='LoginForm_Login_Button']": FakeElement(),
        })
        self.assertEqual(finish(login_twitter(page, "user", "password", log)), LoginStatus.LOGGED_OUT)

    def test_google_continue_query_is_not_youtube_success(self):
        page = FakePage(
            "https://accounts.google.com/ServiceLogin?service=youtube&continue=https://www.youtube.com/"
        )
        page.elements.update({
            "css:input[type='email']": FakeElement(),
            "css:input[type='password']": FakeElement(),
            "css:#identifierNext": FakeElement(),
            "css:#passwordNext": FakeElement(),
        })
        self.assertEqual(finish(login_youtube(page, "user", "password", log)), LoginStatus.LOGGED_OUT)

    def test_platform_wait_stops_immediately_when_cancelled(self):
        page = FakePage("https://www.facebook.com/")
        page.elements.update({
            "css:input[name='email']": FakeElement(),
            "css:input[name='pass']": FakeElement(),
        })
        cancelled = threading.Event()
        cancelled.set()
        self.assertEqual(
            finish(login_facebook(page, "user", "password", log, cancelled)),
            LoginStatus.LOGGED_OUT,
        )


if __name__ == "__main__":
    unittest.main()