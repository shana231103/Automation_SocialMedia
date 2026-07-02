# File: backend/tests/unit/automation/test_platforms_facebook.py
"""Unit tests for Facebook platform login script utilizing Mock Automation interfaces."""

import unittest
from typing import Generator, Any, List
from app.domain.models import LoginStatus
from app.infrastructure.automation.page_wrapper import AutomationPage, AutomationElement
from app.infrastructure.automation.platforms.facebook import login_facebook


class MockElement(AutomationElement):
    """Mock implementation of AutomationElement."""

    def __init__(self, selector: str):
        self.selector = selector
        self.input_history = []
        self.clicks = 0
        self.presses = []
        self.is_present = True

    def input(self, text: str) -> None:
        self.input_history.append(text)

    def click(self, by_js: bool = False) -> None:
        self.clicks += 1

    def press(self, key: str) -> None:
        self.presses.append(key)

    def exists(self) -> bool:
        return self.is_present


class MockPage(AutomationPage):
    """Mock implementation of AutomationPage."""

    def __init__(self, initial_url: str):
        self._url = initial_url
        self._html = "<html></html>"
        self.navigated_urls = []
        self.elements = {}

    def goto(self, url: str) -> None:
        self._url = url
        self.navigated_urls.append(url)

    def find(self, selector: str, timeout: float = 5.0) -> AutomationElement | None:
        return self.elements.get(selector)

    def find_first(self, *selectors: str, timeout: float = 5.0) -> AutomationElement | None:
        for selector in selectors:
            if selector in self.elements:
                return self.elements[selector]
        return None

    @property
    def url(self) -> str:
        return self._url

    @url.setter
    def url(self, val: str):
        self._url = val

    @property
    def html(self) -> str:
        return self._html

    @html.setter
    def html(self, val: str):
        self._html = val


class TestFacebookLoginScript(unittest.TestCase):
    """Test suite for Facebook platform login workflow."""

    def setUp(self):
        self.page = MockPage("https://www.facebook.com/")
        self.logs = []

        def log_func(msg: str):
            self.logs.append(msg)
            return {"type": "log", "message": msg}
        self.log_func = log_func

    def test_already_logged_in(self):
        # Set up page state indicating logged in
        self.page.elements["css:[role='feed']"] = MockElement("css:[role='feed']")
        
        gen = login_facebook(self.page, "user", "pass", self.log_func)
        
        # Run generator completely to catch StopIteration and get return value
        result = None
        try:
            while True:
                next(gen)
        except StopIteration as stop:
            result = stop.value
            
        self.assertEqual(result, LoginStatus.LOGGED_IN)
        self.assertIn("Đã phát hiện phiên đăng nhập sẵn có.", self.logs)

    def test_successful_login_flow(self):
        # Input elements present
        email_el = MockElement("css:input[name='email']")
        pass_el = MockElement("css:input[name='pass']")
        login_btn = MockElement("css:button[name='login']")
        
        self.page.elements["css:input[name='email']"] = email_el
        self.page.elements["css:input[name='pass']"] = pass_el
        self.page.elements["css:button[name='login']"] = login_btn
        
        gen = login_facebook(self.page, "test_user", "test_pass", self.log_func)
        
        # Mock redirects during dynamic polling loop (20 iterations)
        # We simulate login success after 3 iterations
        states = [
            ("https://www.facebook.com/", False),
            ("https://www.facebook.com/", False),
            ("https://www.facebook.com/home.php", True),
        ]
        
        def run_polling_states():
            idx = 0
            while True:
                yield
                if idx < len(states):
                    self.page.url = states[idx][0]
                    if states[idx][1]:
                        self.page.elements["css:[role='feed']"] = MockElement("css:[role='feed']")
                    idx += 1

        state_gen = run_polling_states()

        # Execute generator and handle sleep mocking if needed, or simply exhaust
        result = None
        # Mock time.sleep to speed up test execution
        import time
        original_sleep = time.sleep
        time.sleep = lambda s: next(state_gen) if s == 0.5 else None
        
        try:
            while True:
                next(gen)
        except StopIteration as stop:
            result = stop.value
        finally:
            time.sleep = original_sleep

        self.assertEqual(result, LoginStatus.LOGGED_IN)
        self.assertEqual(email_el.input_history, ["test_user"])
        self.assertEqual(pass_el.input_history, ["test_pass"])
        self.assertEqual(login_btn.clicks, 1)
        self.assertIn("Đăng nhập thành công vào trang chủ.", self.logs)



if __name__ == "__main__":
    unittest.main()
