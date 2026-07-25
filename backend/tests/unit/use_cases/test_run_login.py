# File: backend/tests/unit/use_cases/test_run_login.py
"""Unit tests for unified RunLoginUseCase supporting single and batch executions."""

import unittest
import asyncio
from unittest.mock import MagicMock
from app.domain.models import Account, Platform, LoginStatus
from app.application.use_cases.run_login import RunLoginUseCase


class TestRunLoginUseCase(unittest.TestCase):
    """Test suite for unified RunLoginUseCase logic."""

    def setUp(self):
        self.mock_account = Account(
            id=1,
            username="testuser",
            password="password123",
            platform=Platform.FACEBOOK,
            status=LoginStatus.LOGGED_OUT,
            gemlogin_profile_name=None
        )
        self.mock_account_repo = MagicMock()
        self.mock_account_repo.get_by_id.return_value = self.mock_account

        self.mock_history_repo = MagicMock()

        self.mock_automation_service = MagicMock()
        self.mock_automation_service.run_login.return_value = [
            {"type": "log", "message": "Executing mock login..."},
            {"type": "result", "status": LoginStatus.LOGGED_IN, "logs": "Success"}
        ]

    def test_single_run_defaults_to_slot_1_profile(self):
        # Account has no gemlogin_profile_name set (None)
        use_case = RunLoginUseCase(
            account_repo=self.mock_account_repo,
            history_repo=self.mock_history_repo,
            automation_service=self.mock_automation_service
        )

        events = list(use_case.execute(1))

        # Check target_profile_name passed to automation service is "1" instead of "facebook_1"
        self.mock_automation_service.run_login.assert_called_once_with(
            "testuser",
            "password123",
            Platform.FACEBOOK,
            "facebook_1",
            "1"
        )
        
        # Verify account status updated and saved
        self.mock_account_repo.save.assert_called_once()
        self.mock_history_repo.save.assert_called_once()

        # Check done event yielded
        self.assertEqual(events[-1]["type"], "done")

    def test_single_run_uses_custom_gemlogin_profile_name(self):
        # Account has explicit gemlogin_profile_name set
        self.mock_account.gemlogin_profile_name = "MyGemProfile_A"

        use_case = RunLoginUseCase(
            account_repo=self.mock_account_repo,
            history_repo=self.mock_history_repo,
            automation_service=self.mock_automation_service
        )

        list(use_case.execute(1))

        # Check target_profile_name passed to automation service matches custom profile name
        self.mock_automation_service.run_login.assert_called_once_with(
            "testuser",
            "password123",
            Platform.FACEBOOK,
            "facebook_1",
            "MyGemProfile_A"
        )

    def test_batch_run_uses_isolated_session_factory_and_slot_pool(self):
        mock_sessions = []
        def mock_session_factory():
            session = MagicMock()
            mock_sessions.append(session)
            return session

        use_case = RunLoginUseCase(
            account_repo=self.mock_account_repo,
            history_repo=self.mock_history_repo,
            automation_service=self.mock_automation_service,
            max_concurrent=2,
            session_factory=mock_session_factory
        )

        async def run_test():
            events = []
            async for event in use_case.execute_batch([1]):
                events.append(event)
            return events

        events = asyncio.run(run_test())

        # Verify worker opened and closed a dedicated session
        self.assertEqual(len(mock_sessions), 1)
        mock_sessions[0].close.assert_called_once()

        # Verify summary event was generated
        summary_events = [e for e in events if e.get("type") == "batch_summary"]
        self.assertEqual(len(summary_events), 1)
        self.assertEqual(summary_events[0]["total"], 1)


if __name__ == "__main__":
    unittest.main()
