# File: backend/tests/unit/automation/test_locator_registries.py
"""Coverage for immutable platform semantic locator registries."""

import unittest

from app.domain.models import Platform
from app.infrastructure.automation.locators import get_locator_spec
from app.infrastructure.automation.semantic_types import SemanticIntent


class LocatorRegistryTests(unittest.TestCase):
    def test_target_platforms_expose_expected_intents(self):
        expected = {
            Platform.TIKTOK: {
                SemanticIntent.EMAIL_OR_PHONE_INPUT,
                SemanticIntent.PASSWORD_INPUT,
                SemanticIntent.LOGIN_SUBMIT_CONTROL,
            },
            Platform.YOUTUBE: set(SemanticIntent),
            Platform.TWITTER: set(SemanticIntent),
        }
        for platform, intents in expected.items():
            with self.subTest(platform=platform):
                found = {
                    intent for intent in SemanticIntent
                    if get_locator_spec(platform, intent) is not None
                }
                self.assertEqual(found, intents)

    def test_specs_have_unique_bounded_candidates(self):
        for platform in Platform:
            for intent in SemanticIntent:
                spec = get_locator_spec(platform, intent)
                if spec is None:
                    continue
                with self.subTest(platform=platform, intent=intent):
                    self.assertTrue(spec.hint_text.strip())
                    self.assertEqual(len(spec.selectors), len(set(spec.selectors)))
                    self.assertTrue(all(selector.strip() for selector in spec.selectors))
                    self.assertGreater(spec.timeout_seconds, 0)
                    self.assertLessEqual(spec.timeout_seconds, 10)

    def test_tiktok_continue_is_deliberately_unsupported(self):
        self.assertIsNone(
            get_locator_spec(Platform.TIKTOK, SemanticIntent.CONTINUE_CONTROL)
        )


if __name__ == "__main__":
    unittest.main()
