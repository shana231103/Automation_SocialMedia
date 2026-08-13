# File: backend/tests/unit/automation/test_ai_login_context.py
"""Per-login budget, usage, cancellation, and terminal reuse tests."""

import threading
import unittest

from app.application.ai_login import AICapability, AIUsage, TerminalAssessment
from app.domain.models import LoginStatus
from app.infrastructure.ai.config import AILimits
from app.infrastructure.automation.ai_login_context import AILoginContextFactory


class AILoginContextTests(unittest.TestCase):
    def test_call_budget_counts_actual_reservations(self):
        limits = AILimits(max_calls_per_login=2, max_concurrent_requests=1)
        context = AILoginContextFactory(limits).create()
        first = context.reserve_call(AICapability.SELECTOR)
        self.assertTrue(first.granted)
        first.release()
        second = context.reserve_call(AICapability.TERMINAL_ASSESSMENT)
        self.assertTrue(second.granted)
        second.release()
        self.assertFalse(context.reserve_call(AICapability.SELECTOR).granted)
        self.assertEqual(context.snapshot_metrics().calls, 2)

    def test_terminal_reuse_requires_exact_observation_identity(self):
        context = AILoginContextFactory(AILimits()).create()
        assessment = TerminalAssessment(LoginStatus.LOGGED_OUT, .9, "safe", "one")
        context.remember_terminal("one", assessment)
        self.assertIs(context.matching_terminal("one"), assessment)
        self.assertIsNone(context.matching_terminal("two"))
        self.assertEqual(context.snapshot_metrics().terminal_reuse_hits, 1)

    def test_cancellation_fails_closed(self):
        event = threading.Event()
        context = AILoginContextFactory(AILimits()).create(event)
        event.set()
        self.assertFalse(context.reserve_call(AICapability.SELECTOR).granted)

    def test_usage_is_safe_and_aggregated(self):
        context = AILoginContextFactory(AILimits()).create()
        context.record_usage(AIUsage(10, 4, 14))
        metrics = context.snapshot_metrics()
        self.assertEqual((metrics.input_tokens, metrics.output_tokens), (10, 4))
        self.assertNotIn("screenshot", metrics.__dict__)

    def test_limiter_rejection_does_not_count_as_transport_attempt(self):
        factory = AILoginContextFactory(AILimits(
            selector_timeout=.001, status_timeout=.001,
            max_concurrent_requests=1))
        occupied, waiting = factory.create(), factory.create()
        reservation = occupied.reserve_call(AICapability.SELECTOR)
        self.assertFalse(waiting.reserve_call(AICapability.SELECTOR).granted)
        self.assertEqual(waiting.snapshot_metrics().calls, 0)
        reservation.release()


if __name__ == "__main__":
    unittest.main()
