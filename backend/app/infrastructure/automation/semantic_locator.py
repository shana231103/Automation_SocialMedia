"""Shared AI-first semantic locator and legacy selector fallback policy."""

import re
import threading

from app.domain.models import Platform
from app.infrastructure.ai.dom_parser import DOMParser
from app.infrastructure.ai.vision_client import (
    ElementPrediction, MultimodalVisionClient, SelectorPredictionFailure, VisionClient,
)
from app.infrastructure.automation.locators import get_locator_spec
from app.infrastructure.automation.page_wrapper import AutomationElement, AutomationPage
from app.infrastructure.automation.semantic_types import (
    ResolutionFailure, ResolutionSource, SemanticIntent, SemanticResolution,
)


class SemanticLocatorResolver:
    """Resolve semantic element intents with bounded AI and registry fallback."""

    MIN_CONFIDENCE, MAX_AI_ATTEMPTS, PREDICTED_SELECTOR_TIMEOUT = 0.80, 2, 2.0

    def __init__(
        self,
        vision_client: VisionClient | None = None,
        min_confidence: float = 0.80,
        predicted_selector_timeout: float = 2.0,
    ) -> None:
        if not 0 <= min_confidence <= 1:
            raise ValueError("Semantic confidence threshold is invalid")
        if not 0 < predicted_selector_timeout <= 10:
            raise ValueError("Predicted selector timeout is invalid")
        self.configuration_error = ""
        if vision_client is None:
            try:
                vision_client = MultimodalVisionClient()
            except (TypeError, ValueError):
                self.configuration_error = "AI selector configuration is invalid"
        self.vision_client = vision_client
        self.min_confidence = min_confidence
        self.predicted_selector_timeout = predicted_selector_timeout

    def resolve(
        self, page: AutomationPage, platform: Platform, intent: SemanticIntent,
        cancellation_event: threading.Event | None = None,
    ) -> SemanticResolution[AutomationElement]:
        spec = get_locator_spec(platform, intent)
        if spec is None:
            return self._unresolved(ResolutionFailure.REGISTRY_MISSING, "Locator registry entry is missing")
        if self._is_cancelled(cancellation_event):
            return self._unresolved(ResolutionFailure.CANCELLED, "Semantic resolution was cancelled")
        attempts, last = 0, None
        if self._enabled():
            for attempt in range(self.MAX_AI_ATTEMPTS):
                if self._is_cancelled(cancellation_event):
                    return self._cancelled(attempts, last)
                prediction = self._predict_once(page, spec.hint_text, cancellation_event)
                attempts += 1
                last = prediction
                if self._is_cancelled(cancellation_event):
                    return self._cancelled(attempts, last)
                element = self._find_predicted(page, prediction)
                if element is not None:
                    return SemanticResolution(
                        element, ResolutionSource.AI, ResolutionFailure.NONE,
                        attempts, prediction.confidence, self._reason(prediction.reasoning),
                    )
                if attempt + 1 >= self.MAX_AI_ATTEMPTS or not self._is_retryable(
                    prediction, element is not None, self.min_confidence,
                ):
                    break
        else:
            last = ElementPrediction(
                failure_code=SelectorPredictionFailure.DISABLED,
                reasoning=self.configuration_error or "Ollama selector fallback is disabled")
        if self._is_cancelled(cancellation_event):
            return self._cancelled(attempts, last)
        try:
            element = page.find_first(*spec.selectors, timeout=spec.timeout_seconds)
        except Exception:
            return self._unresolved(
                ResolutionFailure.UNEXPECTED_ERROR, "Deterministic locator fallback failed",
                attempts, last)
        if element is not None:
            return SemanticResolution(
                element, ResolutionSource.REGISTRY, ResolutionFailure.NONE,
                attempts, last.confidence if last else 0.0,
                self._reason(last.reasoning if last else "Resolved by deterministic registry"),
            )
        return self._unresolved(
            ResolutionFailure.NOT_FOUND,
            "AI and deterministic locators did not resolve the element",
            attempts, last)

    def resolve_legacy(
        self, page: AutomationPage, selector: str, hint_text: str, timeout: float = 5.0,
    ) -> AutomationElement | None:
        try:
            element = page.find(selector, timeout=timeout)
        except Exception:
            element = None
        if element is not None or not self._enabled():
            return element
        prediction = self._predict_once(page, hint_text)
        if prediction.failure_code != SelectorPredictionFailure.NONE or not prediction.selector:
            return None
        try:
            return page.find(prediction.selector, timeout=self.predicted_selector_timeout)
        except Exception:
            return None

    def _predict_once(self, page: AutomationPage, hint_text: str,
                      cancellation_event: threading.Event | None = None) -> ElementPrediction:
        if self.vision_client is None:
            return ElementPrediction(
                failure_code=SelectorPredictionFailure.DISABLED,
                reasoning="Ollama selector fallback is unavailable")
        try:
            image = page.capture_screenshot_base64(mask_sensitive=True)
            dom = DOMParser.extract_interactable_snippet(page.html)
            if self._is_cancelled(cancellation_event):
                return ElementPrediction(
                    failure_code=SelectorPredictionFailure.INCOMPLETE_EVIDENCE,
                    reasoning="Selector prediction was cancelled")
        except Exception:
            return ElementPrediction(
                failure_code=SelectorPredictionFailure.INCOMPLETE_EVIDENCE,
                reasoning="Selector evidence capture failed")
        try:
            return self.vision_client.predict_element(image, dom, hint_text)
        except Exception:
            return ElementPrediction(
                failure_code=SelectorPredictionFailure.UNAVAILABLE,
                reasoning="Selector prediction failed unexpectedly")

    def _find_predicted(
        self, page: AutomationPage, prediction: ElementPrediction,
    ) -> AutomationElement | None:
        if (
            prediction.failure_code != SelectorPredictionFailure.NONE
            or not prediction.selector
            or prediction.confidence < self.min_confidence
        ):
            return None
        try:
            return page.find(prediction.selector, timeout=self.predicted_selector_timeout)
        except Exception:
            return None

    @staticmethod
    def _is_retryable(prediction: ElementPrediction, element_found: bool,
                      min_confidence: float) -> bool:
        if prediction.failure_code == SelectorPredictionFailure.NONE:
            return not prediction.selector or prediction.confidence < min_confidence or not element_found
        return prediction.failure_code in {
            SelectorPredictionFailure.TIMEOUT,
            SelectorPredictionFailure.UNAVAILABLE,
            SelectorPredictionFailure.HTTP_SERVER_ERROR,
            SelectorPredictionFailure.INVALID_RESPONSE,
        }

    @staticmethod
    def _is_cancelled(event: threading.Event | None) -> bool:
        return bool(event and event.is_set())

    def _enabled(self) -> bool:
        try:
            return bool(self.vision_client and self.vision_client.is_enabled())
        except Exception:
            return False

    @classmethod
    def _cancelled(cls, attempts: int,
                   prediction: ElementPrediction | None) -> SemanticResolution[AutomationElement]:
        return cls._unresolved(
            ResolutionFailure.CANCELLED, "Semantic resolution was cancelled", attempts, prediction,
        )

    @classmethod
    def _unresolved(cls, failure: ResolutionFailure, reason: str, attempts: int = 0,
                    prediction: ElementPrediction | None = None,
    ) -> SemanticResolution[AutomationElement]:
        return SemanticResolution(
            None, ResolutionSource.NONE, failure, attempts,
            prediction.confidence if prediction else 0.0, cls._reason(reason),
        )

    @staticmethod
    def _reason(reason: str) -> str:
        return re.sub(r"[\x00-\x1f\x7f]", " ", reason).strip()[:240]
