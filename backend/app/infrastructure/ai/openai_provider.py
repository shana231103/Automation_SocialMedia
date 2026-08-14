# File: backend/app/infrastructure/ai/openai_provider.py
"""OpenAI Responses adapter for selector and terminal structured inference."""

from __future__ import annotations

import threading
from typing import Any, TypeVar

from pydantic import BaseModel

from app.application.ai_login import (
    AIFailureCode, AILoginStrategy, AIProviderHealth, AIUsage, ProtectedObservation,
    SelectorAssessment, SelectorBatchAssessment, SelectorInferencePort,
    TerminalAssessment, TerminalAssessmentPort,
    AIHealthPort,
)
from app.domain.models import LoginStatus
from app.infrastructure.ai.openai_schemas import (
    OpenAISelectorBatchWire, OpenAISelectorWire, OpenAIStatusWire,
)
from app.infrastructure.ai.provider_errors import map_provider_error
from app.infrastructure.ai.status_policy import STATUS_MAP

T = TypeVar("T", bound=BaseModel)


class OpenAIProvider(SelectorInferencePort, TerminalAssessmentPort, AIHealthPort):
    provider = "openai"

    def __init__(self, api_key: str, selector_model: str, status_model: str,
                 selector_timeout: float = 20,
                 status_timeout: float = 60, client: Any | None = None) -> None:
        self.selector_model, self.status_model = selector_model, status_model
        self.selector_timeout, self.status_timeout = selector_timeout, status_timeout
        if client is None:
            from openai import OpenAI
            options: dict[str, Any] = {"api_key": api_key, "max_retries": 0}
            client = OpenAI(**options)
        self._client = client

    def predict_selector(self, observation: ProtectedObservation, intent: str,
                         cancellation_event: threading.Event | None = None) -> SelectorAssessment:
        if cancellation_event and cancellation_event.is_set():
            return self._selector_failure(AIFailureCode.CANCELLED, "Selector request cancelled")
        prompt = ("Return the best CSS or XPath selector for the requested login control. "
                  "Return null when evidence is insufficient. Never repeat DOM values. "
                  f"Target: {intent}\nDOM:\n{observation.dom_snippet}")
        try:
            wire, usage = self._parse(self.selector_model, prompt, observation,
                                      OpenAISelectorWire, self.selector_timeout)
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
        prompt = ("Return one CSS or XPath selector, or null, for every requested login control. "
                  "Use each target intent exactly once and never repeat DOM values. Targets: " +
                  ", ".join(intents) + f"\nDOM:\n{observation.dom_snippet}")
        try:
            wire, usage = self._parse(self.selector_model, prompt, observation,
                                      OpenAISelectorBatchWire, self.selector_timeout)
            if {item.intent for item in wire.selectors} != set(intents):
                raise ValueError("OpenAI selector batch did not cover every requested intent")
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
        prompt = ("Classify login status as logged_in, logged_out, checkpoint, or dead. "
                  "CAPTCHA, MFA, challenge, or verification is checkpoint. Never expose secrets. "
                  f"Preliminary: {preliminary_status.value}. URL: {observation.redacted_url}. "
                  f"DOM:\n{observation.dom_snippet}")
        try:
            wire, usage = self._parse(self.status_model, prompt, observation,
                                      OpenAIStatusWire, self.status_timeout)
            return TerminalAssessment(STATUS_MAP[wire.status], wire.confidence, wire.reasoning,
                                      observation.observation_id, tuple(wire.visual_evidence),
                                      tuple(wire.dom_evidence), wire.agreement, self.provider,
                                      self.status_model, usage)
        except Exception as exc:
            code, reason = map_provider_error(exc)
            return self._terminal_failure(observation.observation_id, code, reason)

    def get_health(self) -> AIProviderHealth:
        return AIProviderHealth(True, self.provider, AILoginStrategy.SEMANTIC.value,
                                (self.selector_model, self.status_model), True, None,
                                ("selector", "terminal_assessment"),
                                "OpenAI is configured; runtime calls are health-checked on use")

    def _parse(self, model: str, prompt: str, observation: ProtectedObservation,
               schema: type[T], timeout: float) -> tuple[T, AIUsage]:
        response = self._client.responses.parse(
            model=model, text_format=schema, timeout=timeout,
            input=[{"role": "user", "content": [
                {"type": "input_text", "text": prompt},
                {"type": "input_image", "image_url":
                 f"data:image/png;base64,{observation.screenshot_base64}"},
            ]}],
        )
        for output in response.output:
            for content in getattr(output, "content", ()):
                parsed = getattr(content, "parsed", None)
                if isinstance(parsed, schema):
                    usage = getattr(response, "usage", None)
                    return parsed, AIUsage(int(getattr(usage, "input_tokens", 0) or 0),
                                           int(getattr(usage, "output_tokens", 0) or 0),
                                           int(getattr(usage, "total_tokens", 0) or 0))
        raise ValueError("OpenAI returned no parsed structured output")

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
