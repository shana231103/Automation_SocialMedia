"""Unit tests for shared semantic and legacy element resolution policy."""

import threading
import unittest

from app.application.ai_login import AIUsage, SelectorAssessment, SelectorBatchAssessment
from app.domain.models import Platform
from app.infrastructure.ai.config import AILimits
from app.infrastructure.ai.vision_client import (
    ElementPrediction, SelectorPredictionFailure,
)
from app.infrastructure.automation.locators import get_locator_spec
from app.infrastructure.automation.ai_login_context import AILoginContextFactory
from app.infrastructure.automation.semantic_locator import SemanticLocatorResolver
from app.infrastructure.automation.semantic_types import (
    ResolutionFailure, ResolutionSource, SemanticIntent,
)


class FakeClient:
    def __init__(self, predictions, enabled=True, event=None):
        self.predictions = list(predictions)
        self.enabled = enabled
        self.event = event
        self.calls = 0

    def is_enabled(self):
        return self.enabled

    def predict_element(self, image, dom, hint):
        prediction = self.predictions[min(self.calls, len(self.predictions) - 1)]
        self.calls += 1
        if self.event:
            self.event.set()
        return prediction
class FakePage:
    def __init__(self, elements=None):
        self.elements = elements or {}
        self.find_calls = []
        self.first_calls = []
        self.capture_calls = 0
        self.cancel_on_capture = None
        self.capture_error = False
        self.html = '<input name="email"><button type="submit">Log in</button>'
        self.url = "https://www.facebook.com/"

    def find(self, selector, timeout=5.0):
        self.find_calls.append((selector, timeout))
        return self.elements.get(selector)

    def find_first(self, *selectors, timeout=5.0):
        self.first_calls.append((selectors, timeout))
        return next((self.elements[item] for item in selectors if item in self.elements), None)

    def capture_screenshot_base64(self, mask_sensitive=True):
        self.capture_calls += 1
        if self.capture_error:
            raise RuntimeError("capture failed")
        if self.cancel_on_capture:
            self.cancel_on_capture.set()
        return "aW1n"


class FakeBatchPort:
    def __init__(self, missing=()):
        self.calls = 0
        self.missing = set(missing)

    def predict_selectors(self, observation, intents, cancellation_event=None):
        self.calls += 1
        items = tuple((intent, SelectorAssessment(
            f"css:#{intent}", .91, "visible", "fake", "model",
        )) for intent in intents if intent not in self.missing)
        return SelectorBatchAssessment(items, AIUsage(30, 6, 36))
def prediction(selector=None, confidence=0.0, failure=SelectorPredictionFailure.NONE):
    return ElementPrediction(
        selector=selector, confidence=confidence, reasoning="test", failure_code=failure,
    )
class SemanticLocatorTests(unittest.TestCase):
    def test_batch_resolves_three_intents_with_one_provider_call_and_one_usage_record(self):
        intents = (SemanticIntent.EMAIL_OR_PHONE_INPUT, SemanticIntent.PASSWORD_INPUT,
                   SemanticIntent.LOGIN_SUBMIT_CONTROL)
        elements = {f"css:#{intent.value}": object() for intent in intents}
        port = FakeBatchPort()
        context = AILoginContextFactory(AILimits()).create()
        results = SemanticLocatorResolver(port, context).resolve_many(
            FakePage(elements), Platform.FACEBOOK, intents,
        )
        self.assertEqual(port.calls, 1)
        self.assertTrue(all(result.source == ResolutionSource.AI for result in results.values()))
        metrics = context.snapshot_metrics()
        self.assertEqual((metrics.calls, metrics.input_tokens, metrics.output_tokens), (1, 30, 6))

    def test_batch_uses_registry_only_for_an_omitted_intent(self):
        missing = SemanticIntent.PASSWORD_INPUT
        intents = (SemanticIntent.EMAIL_OR_PHONE_INPUT, missing,
                   SemanticIntent.LOGIN_SUBMIT_CONTROL)
        elements = {f"css:#{intent.value}": object() for intent in intents if intent != missing}
        elements["css:input[name='pass']"] = object()
        results = SemanticLocatorResolver(
            FakeBatchPort({missing.value}), AILoginContextFactory(AILimits(
                max_selector_attempts=1)).create(),
        ).resolve_many(FakePage(elements), Platform.FACEBOOK, intents)
        self.assertEqual(results[missing].source, ResolutionSource.REGISTRY)
        self.assertEqual(results[SemanticIntent.EMAIL_OR_PHONE_INPUT].source, ResolutionSource.AI)
    def test_facebook_registry_is_complete_ordered_and_immutable(self):
        expected = {
            SemanticIntent.EMAIL_OR_PHONE_INPUT: ("css:input[name='email']", 1.5),
            SemanticIntent.PASSWORD_INPUT: ("css:input[name='pass']", 1.5),
            SemanticIntent.CONTINUE_CONTROL: ("text:Continue", 2.0),
            SemanticIntent.LOGIN_SUBMIT_CONTROL: ("css:button[name='login']", 3.0),
        }
        for intent, (first, budget) in expected.items():
            spec = get_locator_spec(Platform.FACEBOOK, intent)
            self.assertEqual((spec.selectors[0], spec.timeout_seconds), (first, budget))
        self.assertIsNone(get_locator_spec(Platform.TIKTOK, SemanticIntent.CONTINUE_CONTROL))

    def test_ai_first_success(self):
        element = object()
        client = FakeClient([prediction("css:#ai", 0.91)])
        page = FakePage({"css:#ai": element})
        result = SemanticLocatorResolver(client).resolve(
            page, Platform.FACEBOOK, SemanticIntent.EMAIL_OR_PHONE_INPUT,
        )
        self.assertIs(result.element, element)
        self.assertEqual((result.source, result.ai_attempts), (ResolutionSource.AI, 1))
        self.assertFalse(page.first_calls)
    def test_each_retryable_failure_can_recover_on_second_attempt(self):
        retryable = (
            SelectorPredictionFailure.TIMEOUT,
            SelectorPredictionFailure.UNAVAILABLE,
            SelectorPredictionFailure.HTTP_SERVER_ERROR,
            SelectorPredictionFailure.INVALID_RESPONSE,
        )
        for failure in retryable:
            with self.subTest(failure=failure):
                element = object()
                client = FakeClient([
                    prediction(failure=failure), prediction("css:#ai", 0.9),
                ])
                result = SemanticLocatorResolver(client).resolve(
                    FakePage({"css:#ai": element}), Platform.FACEBOOK,
                    SemanticIntent.PASSWORD_INPUT,
                )
                self.assertIs(result.element, element)
                self.assertEqual(client.calls, 2)
    def test_rejected_predictions_retry_then_use_registry(self):
        rejected = (
            prediction(None, 0.9),
            prediction("css:#ai", 0.79),
            prediction("css:#missing", 0.9),
        )
        for first in rejected:
            with self.subTest(prediction=first):
                registry = object()
                page = FakePage({"css:input[name='email']": registry})
                client = FakeClient([first, first])
                result = SemanticLocatorResolver(client).resolve(
                    page, Platform.FACEBOOK, SemanticIntent.EMAIL_OR_PHONE_INPUT,
                )
                self.assertIs(result.element, registry)
                self.assertEqual((result.source, client.calls), (ResolutionSource.REGISTRY, 2))
    def test_non_retryable_failure_uses_registry_immediately(self):
        failures = (
            SelectorPredictionFailure.INCOMPLETE_EVIDENCE,
            SelectorPredictionFailure.HTTP_CLIENT_ERROR,
            SelectorPredictionFailure.REDIRECT_REFUSED,
            SelectorPredictionFailure.RESPONSE_TOO_LARGE,
        )
        for failure in failures:
            with self.subTest(failure=failure):
                client = FakeClient([prediction(failure=failure)])
                resolver = SemanticLocatorResolver(client)
                result = resolver.resolve(
                    FakePage(), Platform.FACEBOOK, SemanticIntent.PASSWORD_INPUT,
                )
                self.assertEqual(result.failure, ResolutionFailure.NOT_FOUND)
                self.assertEqual(client.calls, 1)

    def test_disabled_client_falls_back_without_ai(self):
        element = object()
        client = FakeClient([prediction()], enabled=False)
        page = FakePage({"css:input[name='pass']": element})
        result = SemanticLocatorResolver(client).resolve(
            page, Platform.FACEBOOK, SemanticIntent.PASSWORD_INPUT,
        )
        self.assertIs(result.element, element)
        self.assertEqual((result.source, client.calls), (ResolutionSource.REGISTRY, 0))

        page.capture_error = True
        enabled = FakeClient([prediction("css:#ai", 0.9)])
        result = SemanticLocatorResolver(enabled).resolve(
            page, Platform.FACEBOOK, SemanticIntent.PASSWORD_INPUT,
        )
        self.assertIs(result.element, element)
        self.assertEqual(enabled.calls, 0)

    def test_cancellation_suppresses_ai_retry_and_registry(self):
        event = threading.Event()
        event.set()
        client = FakeClient([prediction("css:#ai", 0.9)])
        page = FakePage()
        result = SemanticLocatorResolver(client).resolve(
            page, Platform.FACEBOOK, SemanticIntent.EMAIL_OR_PHONE_INPUT, event,
        )
        self.assertEqual(result.failure, ResolutionFailure.CANCELLED)
        self.assertEqual((client.calls, len(page.first_calls)), (0, 0))

        event = threading.Event()
        page = FakePage()
        page.cancel_on_capture = event
        result = SemanticLocatorResolver(client).resolve(
            page, Platform.FACEBOOK, SemanticIntent.EMAIL_OR_PHONE_INPUT, event,
        )
        self.assertEqual((result.failure, client.calls), (ResolutionFailure.CANCELLED, 0))

        event = threading.Event()
        client = FakeClient([prediction(failure=SelectorPredictionFailure.TIMEOUT)], event=event)
        page = FakePage()
        result = SemanticLocatorResolver(client).resolve(
            page, Platform.FACEBOOK, SemanticIntent.EMAIL_OR_PHONE_INPUT, event,
        )
        self.assertEqual(result.failure, ResolutionFailure.CANCELLED)
        self.assertEqual((client.calls, len(page.first_calls)), (1, 0))

    def test_legacy_path_remains_selector_first_with_one_ai_call(self):
        static = object()
        client = FakeClient([prediction("css:#ai", 0.1)])
        resolver = SemanticLocatorResolver(client)
        self.assertIs(resolver.resolve_legacy(FakePage({"css:#old": static}), "css:#old", "x"), static)
        self.assertEqual(client.calls, 0)

        predicted = object()
        page = FakePage({"css:#ai": predicted})
        self.assertIs(resolver.resolve_legacy(page, "css:#old", "x"), predicted)
        self.assertEqual(client.calls, 1)


if __name__ == "__main__":
    unittest.main()
