# File: backend/tests/unit/automation/test_action_registry.py
"""Unit tests for Action registry registration and dispatch workflow."""

import unittest
from typing import Generator, Any
from unittest.mock import MagicMock

from app.domain.models import LoginStatus
from app.infrastructure.automation.actions import ACTION_REGISTRY
from app.infrastructure.automation.actions.action_base import AutomationAction
from app.infrastructure.automation.drission_page import DrissionPageAutomationService
from app.infrastructure.automation.page_wrapper import AutomationPage


class DummySuccessAction(AutomationAction):
    """Mock action implementation that succeeds immediately."""

    def execute(self, page: AutomationPage, params: dict[str, Any], log_func) -> str:
        yield log_func("Bắt đầu thực thi hành động giả lập...")
        return "SUCCESS_RESULT"


class TestActionRegistry(unittest.TestCase):
    """Test suite validating dynamic action dispatch logic in services."""

    def test_default_registration(self):
        # Default registration should contain login action
        self.assertIn("login", ACTION_REGISTRY)

    def test_run_action_dispatch(self):
        # 1. Register a temporary dummy action in registry
        ACTION_REGISTRY["dummy_success"] = DummySuccessAction

        try:
            # 2. Mock browser manager context returns a dummy page object
            mock_native_page = MagicMock()
            mock_browser_manager = MagicMock()
            mock_browser_manager.__enter__.return_value = mock_native_page
            mock_browser_manager.get_new_logs.return_value = ["Setup log 1"]

            browser_factory = lambda key, name=None: mock_browser_manager

            # Initialize service with mock browser manager factory
            service = DrissionPageAutomationService(browser_manager_factory=browser_factory)

            # 3. Call run_action
            gen = service.run_action("dummy_success", {"param1": "val1"}, "test_profile")
            
            # 4. Consume generator to check yielded logs and final result
            yielded_items = list(gen)

            # Ensure logs were captured properly
            log_messages = [item["message"] for item in yielded_items if item.get("type") == "log"]
            self.assertIn("Setup log 1", log_messages)
            self.assertIn("Bắt đầu thực thi hành động giả lập...", log_messages)

            # Verify the final result dictionary structure
            result_item = yielded_items[-1]
            self.assertEqual(result_item["type"], "result")
            self.assertEqual(result_item["status"], "SUCCESS_RESULT")
            self.assertIn("Bắt đầu thực thi hành động giả lập...", result_item["logs"])

        finally:
            # Clean up temporary registration
            if "dummy_success" in ACTION_REGISTRY:
                del ACTION_REGISTRY["dummy_success"]

    def test_run_unregistered_action(self):
        # Calling an action that is not in the registry should yield failure logs gracefully
        mock_browser_manager = MagicMock()
        browser_factory = lambda key, name=None: mock_browser_manager
        
        service = DrissionPageAutomationService(browser_manager_factory=browser_factory)
        
        gen = service.run_action("unregistered_action_xxx", {}, "test_profile")
        yielded_items = list(gen)
        
        # Should return result type indicating not registered
        result_item = yielded_items[-1]
        self.assertEqual(result_item["type"], "result")
        self.assertEqual(result_item["status"], LoginStatus.LOGGED_OUT)
        self.assertIn("không được đăng ký trong hệ thống", result_item["logs"])


if __name__ == "__main__":
    unittest.main()
