# File: backend/app/infrastructure/automation/semantic_locator.py
"""Bounded semantic selector inference with deterministic registry fallback."""

import threading

from app.application.ai_login import AICapability, AIFailureCode, SelectorInferencePort
from app.domain.models import Platform
from app.infrastructure.ai.dom_parser import DOMParser
from app.infrastructure.ai.vision_client import ElementPrediction, SelectorPredictionFailure, VisionClient
from app.infrastructure.automation.ai_login_context import AILoginContext
from app.infrastructure.automation.locators import get_locator_spec
from app.infrastructure.automation.page_wrapper import AutomationElement, AutomationPage
from app.infrastructure.automation.protected_observation import capture_protected_observation
from app.infrastructure.automation.semantic_batch_locator import SemanticBatchLocatorMixin
from app.infrastructure.automation.semantic_types import (
    ResolutionFailure, ResolutionSource, SemanticIntent, SemanticResolution,
)


_FAILURE_MAP = {
    AIFailureCode.CANCELLED: SelectorPredictionFailure.CANCELLED,
    AIFailureCode.TIMEOUT: SelectorPredictionFailure.TIMEOUT,
    AIFailureCode.RATE_LIMIT: SelectorPredictionFailure.UNAVAILABLE,
    AIFailureCode.UNAVAILABLE: SelectorPredictionFailure.UNAVAILABLE,
    AIFailureCode.PAYLOAD_TOO_LARGE: SelectorPredictionFailure.RESPONSE_TOO_LARGE,
    AIFailureCode.BUDGET_EXHAUSTED: SelectorPredictionFailure.BUDGET_EXHAUSTED,
    AIFailureCode.DISABLED: SelectorPredictionFailure.DISABLED,
}


class SemanticLocatorResolver(SemanticBatchLocatorMixin):
    MIN_CONFIDENCE, MAX_AI_ATTEMPTS, PREDICTED_SELECTOR_TIMEOUT = 0.80, 2, 2.0

    def __init__(self, selector_port: SelectorInferencePort | VisionClient | None = None,
                 ai_context: AILoginContext | None = None, min_confidence: float = 0.80,
                 predicted_selector_timeout: float = 2.0) -> None:
        if not 0 <= min_confidence <= 1 or not 0 < predicted_selector_timeout <= 10:
            raise ValueError("Semantic locator configuration is invalid")
        self.selector_port = selector_port
        self.ai_context = ai_context
        self.min_confidence = min_confidence
        self.predicted_selector_timeout = predicted_selector_timeout

    def resolve(self, page: AutomationPage, platform: Platform, intent: SemanticIntent,
                cancellation_event: threading.Event | None = None,
                ) -> SemanticResolution[AutomationElement]:
        spec = get_locator_spec(platform, intent)
        if spec is None:
            return self._unresolved(ResolutionFailure.REGISTRY_MISSING, "Locator registry entry is missing")
        if self._cancelled_event(cancellation_event):
            return self._unresolved(ResolutionFailure.CANCELLED, "Semantic resolution was cancelled")
        attempts, last = 0, None
        if self._enabled():
            max_attempts = self.ai_context.limits.max_selector_attempts if self.ai_context else 2
            for attempt in range(max_attempts):
                if self._cancelled_event(cancellation_event):
                    return self._cancelled(attempts, last)
                last = self._predict_once(page, platform, intent, spec.hint_text, cancellation_event)
                attempts += 1
                element = self._find_predicted(page, last)
                if element is not None:
                    return SemanticResolution(element, ResolutionSource.AI, ResolutionFailure.NONE,
                                              attempts, last.confidence, "AI selector accepted")
                if attempt + 1 >= max_attempts or not self._is_retryable(last):
                    break
        else:
            last = ElementPrediction(failure_code=SelectorPredictionFailure.DISABLED,
                                     reasoning="Remote AI selector assistance is disabled")
        if self._cancelled_event(cancellation_event):
            return self._cancelled(attempts, last)
        return self._fallback(page, spec, attempts, last)

    def _fallback(self, page: AutomationPage, spec, attempts: int,
                  last: ElementPrediction | None) -> SemanticResolution[AutomationElement]:
        try:
            element = page.find_first(*spec.selectors, timeout=spec.timeout_seconds)
        except Exception:
            return self._unresolved(ResolutionFailure.UNEXPECTED_ERROR,
                                    "Deterministic locator fallback failed", attempts, last)
        if element is not None:
            return SemanticResolution(element, ResolutionSource.REGISTRY, ResolutionFailure.NONE,
                                      attempts, last.confidence if last else 0,
                                      "Deterministic registry resolved the element")
        return self._unresolved(ResolutionFailure.NOT_FOUND,
                                "AI and deterministic locators did not resolve the element", attempts, last)

    def resolve_legacy(self, page: AutomationPage, selector: str, hint_text: str,
                       timeout: float = 5.0) -> AutomationElement | None:
        element = page.find(selector, timeout=timeout)
        if element is not None or not self._enabled():
            return element
        prediction = self._predict_once(page, Platform.FACEBOOK,
                                        SemanticIntent.LOGIN_SUBMIT_CONTROL, hint_text, None)
        if prediction.failure_code is not SelectorPredictionFailure.NONE or not prediction.selector:
            return None
        return page.find(prediction.selector, timeout=self.predicted_selector_timeout)

    def _predict_once(self, page: AutomationPage, platform: Platform, intent: SemanticIntent,
                      hint: str, cancellation_event: threading.Event | None) -> ElementPrediction:
        if hasattr(self.selector_port, "predict_element"):
            try:
                image = page.capture_screenshot_base64(True)
                if self._cancelled_event(cancellation_event):
                    return ElementPrediction(failure_code=SelectorPredictionFailure.CANCELLED,
                                             reasoning="Selector request cancelled")
                return self.selector_port.predict_element(
                    image, DOMParser.extract_interactable_snippet(page.html), hint,
                )
            except Exception:
                return ElementPrediction(failure_code=SelectorPredictionFailure.UNAVAILABLE,
                                         reasoning="Selector provider failed")
        if self.selector_port is None or self.ai_context is None:
            return ElementPrediction(failure_code=SelectorPredictionFailure.DISABLED,
                                     reasoning="Selector provider is disabled")
        reservation = self.ai_context.reserve_call(AICapability.SELECTOR)
        if not reservation.granted:
            return ElementPrediction(failure_code=_FAILURE_MAP.get(
                reservation.failure_code, SelectorPredictionFailure.DISABLED),
                reasoning="Selector call budget is unavailable")
        try:
            observation = capture_protected_observation(
                page, platform, None, (), self.ai_context.limits.max_dom_chars,
                self.ai_context.limits.max_screenshot_bytes)
            result = self.selector_port.predict_selector(observation, intent.value, cancellation_event)
            self.ai_context.record_usage(result.usage)
            return self._to_prediction(result)
        except (TypeError, ValueError, RuntimeError):
            return ElementPrediction(failure_code=SelectorPredictionFailure.INCOMPLETE_EVIDENCE,
                                     reasoning="Protected selector evidence is unavailable")
        finally:
            reservation.release()

    @staticmethod
    def _to_prediction(result) -> ElementPrediction:
        if result is None:
            return ElementPrediction(failure_code=SelectorPredictionFailure.INVALID_RESPONSE,
                                     reasoning="Selector batch omitted the requested intent")
        failure = (_FAILURE_MAP.get(result.failure_code, SelectorPredictionFailure.INVALID_RESPONSE)
                   if result.failure_code else SelectorPredictionFailure.NONE)
        return ElementPrediction(selector=result.selector, confidence=result.confidence,
                                 reasoning=result.reason[:500], failure_code=failure)

    def _enabled(self) -> bool:
        if hasattr(self.selector_port, "predict_element") and hasattr(self.selector_port, "is_enabled"):
            return self.selector_port.is_enabled()
        return self.selector_port is not None and self.ai_context is not None

    def _find_predicted(self, page: AutomationPage,
                        prediction: ElementPrediction) -> AutomationElement | None:
        if (prediction.failure_code is not SelectorPredictionFailure.NONE or
                prediction.confidence < self.min_confidence or not prediction.selector):
            return None
        return page.find(prediction.selector, timeout=self.predicted_selector_timeout)

    @staticmethod
    def _is_retryable(prediction: ElementPrediction) -> bool:
        return prediction.failure_code in {
            SelectorPredictionFailure.TIMEOUT, SelectorPredictionFailure.UNAVAILABLE,
            SelectorPredictionFailure.HTTP_SERVER_ERROR, SelectorPredictionFailure.INVALID_RESPONSE,
        } or prediction.failure_code is SelectorPredictionFailure.NONE

    @staticmethod
    def _cancelled_event(event: threading.Event | None) -> bool:
        return bool(event and event.is_set())

    @classmethod
    def _cancelled(cls, attempts: int, last: ElementPrediction | None):
        return cls._unresolved(ResolutionFailure.CANCELLED, "Semantic resolution was cancelled",
                               attempts, last)

    @staticmethod
    def _unresolved(failure: ResolutionFailure, reason: str, attempts: int = 0,
                    last: ElementPrediction | None = None):
        return SemanticResolution(None, ResolutionSource.NONE, failure, attempts,
                                  last.confidence if last else 0, reason[:240])
