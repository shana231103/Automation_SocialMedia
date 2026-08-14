# File: backend/app/infrastructure/ai/gemini_provider.py
"""Gemini adapter for selector and terminal structured inference."""

from __future__ import annotations

import base64
import threading
from typing import Any, TypeVar

from pydantic import BaseModel

from app.application.ai_login import (
    AIFailureCode, AIHealthPort, AILoginStrategy, AIProviderHealth, AIUsage,
    ProtectedObservation, SelectorAssessment, SelectorBatchAssessment, SelectorInferencePort,
    TerminalAssessment, TerminalAssessmentPort,
)
from app.domain.models import LoginStatus
from app.infrastructure.ai.gemini_schemas import (
    GeminiSelectorBatchWire, GeminiSelectorWire, WireAssessment,
)
from app.infrastructure.ai.provider_errors import map_provider_error
from app.infrastructure.ai.status_policy import STATUS_MAP

T = TypeVar("T", bound=BaseModel)


class GeminiProvider(SelectorInferencePort, TerminalAssessmentPort, AIHealthPort):
    provider = "gemini"

    def __init__(self, api_key: str, selector_model: str, status_model: str,
                 selector_timeout: float = 20, status_timeout: float = 60,
                 client: Any | None = None) -> None:
        self.selector_model, self.status_model = selector_model, status_model
        self.selector_timeout, self.status_timeout = selector_timeout, status_timeout
        if client is None:
            from google import genai
            client = genai.Client(
                api_key=api_key,
                http_options={
                    "timeout": int(max(selector_timeout, status_timeout) * 1000),
                    "retry_options": {"attempts": 1},
                },
            )
        self._client = client

    def predict_selector(self, observation: ProtectedObservation, intent: str,
                         cancellation_event: threading.Event | None = None) -> SelectorAssessment:
        if cancellation_event and cancellation_event.is_set():
            return self._selector_failure(AIFailureCode.CANCELLED, "Selector request cancelled")
        prompt = ("Return one CSS/XPath selector for the requested login control, or null. "
                  f"Target: {intent}\nProtected DOM:\n{observation.dom_snippet}")
        try:
            wire, usage = self._generate(self.selector_model, prompt, observation,
                                         GeminiSelectorWire)
            return SelectorAssessment(wire.selector, wire.confidence, wire.reasoning,
                                      self.provider, self.selector_model, usage)
        except Exception as exc:
            code, reason = map_provider_error(exc)
            return self._selector_failure(code, reason)

    def predict_selectors(self, observation: ProtectedObservation, intents: tuple[str, ...],
                          cancellation_event: threading.Event | None = None,
                          ) -> SelectorBatchAssessment:
        if cancellation_event and cancellation_event.is_set():
            return self._batch_failure(intents, AIFailureCode.CANCELLED,
                                       "Selector request cancelled")
        prompt = ("Return one CSS/XPath selector or null for every requested login control. "
                  "Use each target intent exactly once. Targets: " + ", ".join(intents) +
                  f"\nProtected DOM:\n{observation.dom_snippet}")
        try:
            wire, usage = self._generate(self.selector_model, prompt, observation,
                                         GeminiSelectorBatchWire)
            if {item.intent for item in wire.selectors} != set(intents):
                raise ValueError("Gemini selector batch did not cover every requested intent")
            items = tuple((item.intent, SelectorAssessment(
                item.selector, item.confidence, item.reasoning, self.provider, self.selector_model,
            )) for item in wire.selectors)
            return SelectorBatchAssessment(items, usage)
        except Exception as exc:
            code, reason = map_provider_error(exc)
            return self._batch_failure(intents, code, reason)

    def assess_terminal(self, observation: ProtectedObservation,
                        preliminary_status: LoginStatus,
                        cancellation_event: threading.Event | None = None) -> TerminalAssessment:
        if cancellation_event and cancellation_event.is_set():
            return self._terminal_failure(observation.observation_id, AIFailureCode.CANCELLED,
                                          "Terminal assessment cancelled")
        prompt = ("Classify as logged_in, logged_out, checkpoint, or dead. CAPTCHA/MFA/challenge "
                  f"is checkpoint. Preliminary: {preliminary_status.value}. URL: "
                  f"{observation.redacted_url}. DOM:\n{observation.dom_snippet}")
        try:
            wire, usage = self._generate(self.status_model, prompt, observation, WireAssessment)
            return TerminalAssessment(STATUS_MAP[wire.status], wire.confidence, wire.reasoning,
                                      observation.observation_id, tuple(wire.visual_evidence),
                                      tuple(wire.dom_evidence), wire.agreement, self.provider,
                                      self.status_model, usage)
        except Exception as exc:
            code, reason = map_provider_error(exc)
            return self._terminal_failure(observation.observation_id, code, reason)

    def get_health(self) -> AIProviderHealth:
        models = tuple(dict.fromkeys((self.selector_model, self.status_model)))
        return AIProviderHealth(True, self.provider, AILoginStrategy.SEMANTIC.value,
                                models, True, None, ("selector", "terminal_assessment"),
                                "Gemini is configured; runtime calls are health-checked on use")

    def _generate(self, model: str, prompt: str, observation: ProtectedObservation,
                  schema: type[T]) -> tuple[T, AIUsage]:
        image = base64.b64decode(observation.screenshot_base64, validate=True)
        response = self._client.models.generate_content(
            model=model,
            contents=[prompt, {"inline_data": {"mime_type": "image/png", "data": image}}],
            config={"response_mime_type": "application/json",
                    "response_json_schema": schema.model_json_schema(), "temperature": 0},
        )
        wire = schema.model_validate_json(response.text)
        usage = getattr(response, "usage_metadata", None)
        return wire, AIUsage(int(getattr(usage, "prompt_token_count", 0) or 0),
                             int(getattr(usage, "candidates_token_count", 0) or 0),
                             int(getattr(usage, "total_token_count", 0) or 0))

    def _selector_failure(self, code: AIFailureCode, reason: str) -> SelectorAssessment:
        return SelectorAssessment(reason=reason, provider=self.provider,
                                  model=self.selector_model, failure_code=code)

    def _batch_failure(self, intents: tuple[str, ...], code: AIFailureCode,
                       reason: str) -> SelectorBatchAssessment:
        return SelectorBatchAssessment(tuple(
            (intent, self._selector_failure(code, reason)) for intent in intents
        ))

    def _terminal_failure(self, observation_id: str, code: AIFailureCode,
                          reason: str) -> TerminalAssessment:
        return TerminalAssessment(None, 0, reason, observation_id, provider=self.provider,
                                  model=self.status_model, failure_code=code)
