# File: backend/tests/unit/ai/test_ai_routes.py
"""Provider-neutral health route behavior tests."""

import unittest

from app.application.ai_login import (
    AILoginRuntime, AILoginStrategy, AIProviderHealth, AIProviderName,
)
from app.presentation.ai_routes import get_ai_status, router


class Health:
    def get_health(self):
        return AIProviderHealth(
            True, "gemini", "semantic", ("model",), True, None,
            ("selector",), "configured")


class AIRouteTests(unittest.TestCase):
    def test_router_exposes_only_provider_status(self):
        self.assertEqual([route.path for route in router.routes], ["/ai/status"])

    def test_health_is_lightweight_and_secret_safe(self):
        runtime = AILoginRuntime(
            None, None, Health(), AIProviderName.GEMINI, AILoginStrategy.SEMANTIC)
        payload = get_ai_status(runtime)
        self.assertEqual(payload["provider"], "gemini")
        self.assertNotIn("api_key", payload)

if __name__ == "__main__":
    unittest.main()
