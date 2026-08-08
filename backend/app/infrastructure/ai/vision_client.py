# File: backend/app/infrastructure/ai/vision_client.py
"""Loopback Ollama vision client for DOM-assisted element detection."""

import logging
import os
from abc import ABC, abstractmethod
from enum import Enum
from urllib.parse import urlparse

from pydantic import BaseModel, ConfigDict, Field, field_validator
import requests


logger = logging.getLogger(__name__)


class SelectorPredictionFailure(str, Enum):
    """Machine-readable reason that selector prediction did not succeed."""

    NONE = "none"
    DISABLED = "disabled"
    INCOMPLETE_EVIDENCE = "incomplete_evidence"
    TIMEOUT = "timeout"
    UNAVAILABLE = "unavailable"
    HTTP_CLIENT_ERROR = "http_client_error"
    HTTP_SERVER_ERROR = "http_server_error"
    REDIRECT_REFUSED = "redirect_refused"
    RESPONSE_TOO_LARGE = "response_too_large"
    INVALID_RESPONSE = "invalid_response"


class _WireElementPrediction(BaseModel):
    """Schema the model is allowed to produce."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    selector: str | None = Field(default=None, max_length=500)
    confidence: float = Field(default=0.0, ge=0.0, le=1.0)
    reasoning: str = Field(default="", max_length=500)

    @field_validator("selector")
    @classmethod
    def normalize_selector(cls, selector: str | None) -> str | None:
        if not selector or not selector.strip():
            return None
        normalized = selector.strip()
        for prefix in ("css:", "xpath:"):
            if normalized.startswith(prefix):
                return prefix + normalized[len(prefix):].strip()
        return normalized


class ElementPrediction(_WireElementPrediction):
    """Selector prediction enriched with a trusted internal failure code."""

    failure_code: SelectorPredictionFailure = SelectorPredictionFailure.NONE


class VisionClient(ABC):
    """Abstract interface for AI-assisted element detection."""

    @abstractmethod
    def predict_element(
        self, image_base64: str, dom_snippet: str, hint_text: str,
    ) -> ElementPrediction:
        """Predict a selector from a screenshot, compact DOM, and target hint."""
        raise NotImplementedError

    @abstractmethod
    def is_enabled(self) -> bool:
        """Return whether selector fallback is enabled."""
        raise NotImplementedError


class MultimodalVisionClient(VisionClient):
    """Predict selectors with a local Ollama multimodal model."""

    provider = "ollama"

    def __init__(
        self,
        base_url: str | None = None,
        model: str | None = None,
        enabled: bool | None = None,
        connect_timeout: float = 1.0,
        read_timeout: float | None = None,
        max_response_bytes: int = 65536,
        http_session: requests.Session | None = None,
    ) -> None:
        self.base_url = self._validate_local_base_url(
            base_url or os.getenv("OLLAMA_BASE_URL", "http://127.0.0.1:11434"),
        )
        self.model = (model or os.getenv("OLLAMA_MODEL", "qwen3.5:9b")).strip()
        read_timeout = (
            float(os.getenv("OLLAMA_SELECTOR_TIMEOUT_SECONDS", os.getenv("OLLAMA_TIMEOUT_SECONDS", "60")))
            if read_timeout is None else read_timeout
        )
        if not self.model:
            raise ValueError("Ollama model must not be empty")
        if not 0 < connect_timeout <= 10 or not 0 < read_timeout <= 60:
            raise ValueError("Ollama timeouts are outside the allowed range")
        if not 1024 <= max_response_bytes <= 1048576:
            raise ValueError("Ollama response limit is outside the allowed range")
        self.enabled = self._env_enabled() if enabled is None else enabled
        self.connect_timeout = connect_timeout
        self.read_timeout = read_timeout
        self.max_response_bytes = max_response_bytes
        self._session = http_session or requests.Session()

    def is_enabled(self) -> bool:
        return self.enabled

    def predict_element(
        self, image_base64: str, dom_snippet: str, hint_text: str,
    ) -> ElementPrediction:
        if not self.is_enabled():
            return self._failure(
                SelectorPredictionFailure.DISABLED, "Ollama selector fallback is disabled",
            )
        if not image_base64 or not dom_snippet or not hint_text.strip():
            return self._failure(
                SelectorPredictionFailure.INCOMPLETE_EVIDENCE, "Selector evidence is incomplete",
            )
        try:
            response = self._session.post(
                f"{self.base_url}/api/chat",
                json=self._build_payload(image_base64, dom_snippet, hint_text),
                timeout=(self.connect_timeout, self.read_timeout),
                allow_redirects=False,
            )
            if response.is_redirect:
                return self._failure(SelectorPredictionFailure.REDIRECT_REFUSED, "Ollama redirect refused")
            if 400 <= response.status_code < 500:
                return self._failure(
                    SelectorPredictionFailure.HTTP_CLIENT_ERROR,
                    f"Ollama HTTP error {response.status_code}",
                )
            if response.status_code >= 500:
                return self._failure(
                    SelectorPredictionFailure.HTTP_SERVER_ERROR, f"Ollama HTTP error {response.status_code}",
                )
            if isinstance(response.content, bytes) and len(response.content) > self.max_response_bytes:
                return self._failure(
                    SelectorPredictionFailure.RESPONSE_TOO_LARGE, "Ollama response too large",
                )
            message = response.json().get("message")
            if not isinstance(message, dict) or not isinstance(message.get("content"), str):
                raise ValueError("Missing Ollama message content")
            wire = _WireElementPrediction.model_validate_json(message["content"])
            return ElementPrediction(**wire.model_dump())
        except requests.Timeout:
            return self._failure(SelectorPredictionFailure.TIMEOUT, "Ollama selector request timed out")
        except (ValueError, TypeError):
            logger.warning("Ollama selector returned an invalid structured response")
            return self._failure(
                SelectorPredictionFailure.INVALID_RESPONSE,
                "Invalid Ollama selector response",
            )
        except requests.RequestException:
            return self._failure(SelectorPredictionFailure.UNAVAILABLE, "Ollama selector request failed")

    def _build_payload(
        self, image_base64: str, dom_snippet: str, hint_text: str,
    ) -> dict[str, object]:
        prompt = (
            "Locate the requested webpage element using the screenshot and DOM. "
            "Return a usable CSS selector prefixed with css: or XPath prefixed with xpath:. "
            "Return null selector when evidence is insufficient. "
            f"Target: {hint_text.strip()}\nDOM snippet:\n{dom_snippet}"
        )
        return {
            "model": self.model,
            "stream": False,
            "think": False,
            "format": _WireElementPrediction.model_json_schema(),
            "options": {"temperature": 0, "num_predict": 256},
            "messages": [{"role": "user", "content": prompt, "images": [image_base64]}],
        }

    @staticmethod
    def _failure(code: SelectorPredictionFailure, reasoning: str) -> ElementPrediction:
        return ElementPrediction(failure_code=code, reasoning=reasoning)

    @staticmethod
    def _env_enabled() -> bool:
        value = os.getenv("ENABLE_AI_FALLBACK", "true").strip().lower()
        return value in {"true", "1", "yes"}

    @staticmethod
    def _validate_local_base_url(base_url: str) -> str:
        parsed = urlparse(base_url.strip())
        if parsed.scheme not in {"http", "https"} or parsed.hostname not in {
            "127.0.0.1", "localhost", "::1",
        }:
            raise ValueError("OLLAMA_BASE_URL must use a loopback host")
        if parsed.username or parsed.password or parsed.query or parsed.fragment:
            raise ValueError("OLLAMA_BASE_URL must not contain credentials, query, or fragment")
        if parsed.path not in {"", "/"}:
            raise ValueError("OLLAMA_BASE_URL must not contain a path")
        return base_url.strip().rstrip("/")
