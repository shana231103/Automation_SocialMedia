# File: backend/tests/unit/automation/test_page_wrapper.py
"""Unit tests for driver selector translators and page wrappers."""

import unittest
from unittest.mock import MagicMock

from app.infrastructure.automation.adapters.drissionpage_adapter import _to_drission_selector
from app.infrastructure.automation.adapters.playwright_adapter import _to_playwright_selector
from app.infrastructure.automation.adapters.drissionpage_adapter import DrissionPageWrapper
from app.infrastructure.automation.adapters.playwright_adapter import PlaywrightPageWrapper
from playwright.sync_api import TimeoutError as PlaywrightTimeoutError


class TestSelectorTranslation(unittest.TestCase):
    """Test selector translation methods logic."""

    def test_drission_selector_prefixes(self):
        # Already prefixed should not be changed
        self.assertEqual(_to_drission_selector("css:input"), "css:input")
        self.assertEqual(_to_drission_selector("text:X"), "text:X")
        self.assertEqual(_to_drission_selector("xpath://div"), "xpath://div")
        
        # Raw should prepend css:
        self.assertEqual(_to_drission_selector("#email"), "css:#email")
        self.assertEqual(_to_drission_selector("[role='feed']"), "css:[role='feed']")

    def test_playwright_selector_translation(self):
        # Strips css:
        self.assertEqual(_to_playwright_selector("css:input[name='email']"), "input[name='email']")
        # Converts text: to text=
        self.assertEqual(_to_playwright_selector("text:Next"), "text=Next")
        # Strips xpath:
        self.assertEqual(_to_playwright_selector("xpath://button"), "//button")
        # Bare selectors unchanged
        self.assertEqual(_to_playwright_selector("#email"), "#email")
        self.assertEqual(_to_playwright_selector("[role='feed']"), "[role='feed']")


class TestPageWrapperTimeouts(unittest.TestCase):
    """Test timeout distributions in find_first."""

    def test_find_first_calls_find_sequentially(self):
        # Mock DrissionPage Wrapper
        mock_page = MagicMock()
        # Mock .ele to return None (not found)
        mock_page.ele.return_value = None
        
        wrapper = DrissionPageWrapper(mock_page)
        
        # Call find_first with a timeout of 3.0 seconds for 3 selectors
        result = wrapper.find_first("css:#el1", "css:#el2", "css:#el3", timeout=3.0)
        
        self.assertIsNone(result)
        # Should be called with max(0.5, 3.0 / 3) = 1.0s timeout per probe
        self.assertEqual(mock_page.ele.call_count, 3)
        mock_page.ele.assert_any_call("css:#el1", timeout=1.0)
        mock_page.ele.assert_any_call("css:#el2", timeout=1.0)
        mock_page.ele.assert_any_call("css:#el3", timeout=1.0)


if __name__ == "__main__":
    unittest.main()
