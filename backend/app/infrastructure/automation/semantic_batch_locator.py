# File: backend/app/infrastructure/automation/semantic_batch_locator.py
"""Batch semantic selector policy shared by browser adapters."""

import threading

from app.application.ai_login import AICapability, AIFailureCode
from app.domain.models import Platform
from app.infrastructure.ai.vision_client import ElementPrediction, SelectorPredictionFailure
from app.infrastructure.automation.locators import get_locator_spec
from app.infrastructure.automation.page_wrapper import AutomationElement, AutomationPage
from app.infrastructure.automation.protected_observation import capture_protected_observation
from app.infrastructure.automation.semantic_types import (
    ResolutionFailure, ResolutionSource, SemanticIntent, SemanticResolution,
)


class SemanticBatchLocatorMixin:
    """Resolve several intents from one protected provider observation per attempt."""

    def resolve_many(self, page: AutomationPage, platform: Platform,
                     intents: tuple[SemanticIntent, ...],
                     cancellation_event: threading.Event | None = None,
                     ) -> dict[SemanticIntent, SemanticResolution[AutomationElement]]:
        intents = tuple(dict.fromkeys(intents))
        if not hasattr(self.selector_port, "predict_selectors"):
            return {intent: self.resolve(page, platform, intent, cancellation_event)
                    for intent in intents}
        specs = {intent: get_locator_spec(platform, intent) for intent in intents}
        results = {intent: self._unresolved(
            ResolutionFailure.REGISTRY_MISSING, "Locator registry entry is missing",
        ) for intent, spec in specs.items() if spec is None}
        active = tuple(intent for intent in intents if specs[intent] is not None)
        if self._cancelled_event(cancellation_event):
            return {intent: self._unresolved(
                ResolutionFailure.CANCELLED, "Semantic resolution was cancelled",
            ) for intent in intents}
        rounds, last = 0, {}
        attempts = {intent: 0 for intent in active}
        retry = active if self._enabled() else ()
        max_attempts = self.ai_context.limits.max_selector_attempts if self.ai_context else 0
        while retry and rounds < max_attempts:
            predictions = self._predict_many_once(page, platform, retry, cancellation_event)
            rounds += 1
            for intent in retry:
                attempts[intent] += 1
            if self._cancelled_event(cancellation_event):
                return {intent: self._cancelled(attempts.get(intent, 0), predictions.get(intent))
                        for intent in intents}
            next_retry = []
            for intent in retry:
                prediction = predictions[intent]
                last[intent] = prediction
                element = self._find_predicted(page, prediction)
                if element is not None:
                    results[intent] = SemanticResolution(
                        element, ResolutionSource.AI, ResolutionFailure.NONE, attempts[intent],
                        prediction.confidence, "AI selector accepted")
                elif self._is_retryable(prediction):
                    next_retry.append(intent)
            retry = tuple(next_retry)
        if self._cancelled_event(cancellation_event):
            return {intent: self._cancelled(attempts.get(intent, 0), last.get(intent))
                    for intent in intents}
        for intent in active:
            if intent not in results:
                results[intent] = self._fallback(
                    page, specs[intent], attempts[intent], last.get(intent))
        return {intent: results[intent] for intent in intents}

    def _predict_many_once(self, page: AutomationPage, platform: Platform,
                           intents: tuple[SemanticIntent, ...],
                           cancellation_event: threading.Event | None,
                           ) -> dict[SemanticIntent, ElementPrediction]:
        reservation = self.ai_context.reserve_call(AICapability.SELECTOR)
        if not reservation.granted:
            failure = {
                AIFailureCode.CANCELLED: SelectorPredictionFailure.CANCELLED,
                AIFailureCode.BUDGET_EXHAUSTED: SelectorPredictionFailure.BUDGET_EXHAUSTED,
            }.get(reservation.failure_code, SelectorPredictionFailure.DISABLED)
            return {intent: ElementPrediction(failure_code=failure,
                    reasoning="Selector call budget is unavailable") for intent in intents}
        try:
            observation = capture_protected_observation(
                page, platform, None, (), self.ai_context.limits.max_dom_chars,
                self.ai_context.limits.max_screenshot_bytes)
            batch = self.selector_port.predict_selectors(
                observation, tuple(intent.value for intent in intents), cancellation_event)
            self.ai_context.record_usage(batch.usage)
            by_intent = batch.by_intent()
            return {intent: self._to_prediction(by_intent.get(intent.value)) for intent in intents}
        except (TypeError, ValueError, RuntimeError):
            return {intent: ElementPrediction(
                failure_code=SelectorPredictionFailure.INCOMPLETE_EVIDENCE,
                reasoning="Protected selector evidence is unavailable") for intent in intents}
        finally:
            reservation.release()
