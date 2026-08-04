# File: backend/app/infrastructure/ai/ollama_status_verifier.py
"""Local-only Ollama adapter for multimodal account status verification."""

import json
import os
import threading
from urllib.parse import urlparse

import requests

from app.application.status_verification import (
    AccountStatusVerifier,
    StatusVerificationAssessment,
    StatusVerificationEvidence,
    StatusVerifierHealth,
    VerificationFailureCode,
)
from app.domain.models import LoginStatus
from app.infrastructure.ai.ollama_status_response import WireAssessment, hard_evidence_status


_STATUS_MAP = {
    "logged_in": LoginStatus.LOGGED_IN,
    "logged_out": LoginStatus.LOGGED_OUT,
    "checkpoint": LoginStatus.CHECKPOINT,
    "dead": LoginStatus.DEAD,
}


class OllamaStatusVerifier(AccountStatusVerifier):
    """Classify a captured login state through a loopback Ollama endpoint."""

    provider = "ollama"

    def __init__(
        self,
        base_url: str = "http://127.0.0.1:11434",
        model: str = "qwen3.5:9b",
        connect_timeout: float = 1.0,
        read_timeout: float = 20.0,
        max_response_bytes: int = 65536,
        http_session: requests.Session | None = None,
    ) -> None:
        self.base_url = self._validate_local_base_url(base_url)
        self.model = model.strip()
        if not self.model:
            raise ValueError("Ollama model must not be empty")
        if not 0 < connect_timeout <= 10 or not 0 < read_timeout <= 60:
            raise ValueError("Ollama timeouts are outside the allowed range")
        if not 1024 <= max_response_bytes <= 1048576:
            raise ValueError("Ollama response limit is outside the allowed range")
        self.connect_timeout = connect_timeout
        self.read_timeout = read_timeout
        self.max_response_bytes = max_response_bytes
        self._session = http_session or requests.Session()

    @classmethod
    def from_env(cls) -> "OllamaStatusVerifier":
        timeout = float(os.getenv("OLLAMA_TIMEOUT_SECONDS", os.getenv("AI_STATUS_TIMEOUT_SECONDS", "60")))
        return cls(
            base_url=os.getenv("OLLAMA_BASE_URL", "http://127.0.0.1:11434"),
            model=os.getenv("OLLAMA_MODEL", "qwen3.5:9b"),
            connect_timeout=min(1.0, timeout),
            read_timeout=timeout,
        )

    def verify(
        self,
        evidence: StatusVerificationEvidence,
        cancellation_event: threading.Event | None = None,
    ) -> StatusVerificationAssessment:
        if cancellation_event and cancellation_event.is_set():
            return self._failure(VerificationFailureCode.CANCELLED, "Verification cancelled")
        try:
            response = self._session.post(
                f"{self.base_url}/api/chat",
                json=self._build_payload(evidence),
                timeout=(self.connect_timeout, self.read_timeout),
                allow_redirects=False,
            )
        except requests.Timeout:
            return self._failure(VerificationFailureCode.TIMEOUT, "Ollama request timed out")
        except requests.ConnectionError:
            return self._failure(VerificationFailureCode.UNAVAILABLE, "Ollama is unavailable")
        except requests.RequestException:
            return self._failure(VerificationFailureCode.UNAVAILABLE, "Ollama request failed")
        if cancellation_event and cancellation_event.is_set():
            return self._failure(VerificationFailureCode.CANCELLED, "Verification cancelled")
        if response.is_redirect:
            return self._failure(VerificationFailureCode.UNAVAILABLE, "Ollama redirect refused")
        if response.status_code >= 400:
            return self._http_failure(response.status_code, response.text[:500])
        if isinstance(response.content, bytes) and len(response.content) > self.max_response_bytes:
            return self._failure(VerificationFailureCode.INVALID_RESPONSE, "Ollama response too large")
        try:
            return self._parse_response(response.json(), evidence)
        except (ValueError, TypeError, KeyError, json.JSONDecodeError):
            return self._failure(VerificationFailureCode.INVALID_RESPONSE, "Invalid Ollama response")

    def get_status(self) -> StatusVerifierHealth:
        try:
            response = self._session.post(
                f"{self.base_url}/api/show",
                json={"model": self.model},
                timeout=(self.connect_timeout, min(2.0, self.read_timeout)),
                allow_redirects=False,
            )
            if response.status_code >= 400:
                return self._health(False, None, "Model unavailable")
            capabilities = response.json().get("capabilities", [])
            vision = "vision" in capabilities if capabilities else None
            return self._health(True, vision, "Ollama model metadata is available")
        except (requests.RequestException, ValueError, TypeError):
            return self._health(False, None, "Ollama is unreachable")

    def _build_payload(self, evidence: StatusVerificationEvidence) -> dict[str, object]:
        status_code = next(key for key, value in _STATUS_MAP.items() if value == evidence.preliminary_status)
        prompt = (
            "Classify the current social account login state. Do not solve CAPTCHA or 2FA. "
            "Write reasoning, visual_evidence, and dom_evidence in concise Vietnamese. "
            "Cite concrete visible UI and DOM indicators; never repeat credentials. "
            "Use checkpoint for CAPTCHA, challenge, 2FA, or verification screens; "
            "Hard rule: checkpoint, challenge, or captcha in URL/DOM MUST return checkpoint, never logged_out. "
            "use dead only for explicit disabled, suspended, or banned evidence; "
            "use logged_in only for authenticated account UI; otherwise use logged_out. "
            "The chosen status must match the reasoning and evidence. Set agreement true "
            "only when visual and DOM evidence support the same status. "
            f"Platform: {evidence.platform.value}. Preliminary status: {status_code}. "
            f"URL: {evidence.sanitized_url}. DOM evidence:\n{evidence.dom_snippet}"
        )
        return {
            "model": self.model,
            "stream": False,
            "think": False,
            "format": WireAssessment.model_json_schema(),
            "options": {"temperature": 0, "num_predict": 256},
            "messages": [{"role": "user", "content": prompt, "images": [evidence.screenshot_base64]}],
        }

    def _parse_response(
        self, payload: dict[str, object], evidence: StatusVerificationEvidence,
    ) -> StatusVerificationAssessment:
        message = payload["message"]
        if not isinstance(message, dict) or not isinstance(message.get("content"), str):
            raise ValueError("missing message content")
        wire = WireAssessment.model_validate_json(message["content"])
        status, reasoning = _STATUS_MAP[wire.status], wire.reasoning
        hard_status = hard_evidence_status(evidence)
        if hard_status is not None and status != hard_status:
            status = hard_status
            reasoning = (
                "Deterministic URL/DOM evidence corrected an inconsistent AI status to checkpoint. "
                f"AI explanation: {reasoning}"
            )
        return StatusVerificationAssessment(
            status=status, confidence=wire.confidence, reasoning=reasoning,
            visual_evidence=tuple(wire.visual_evidence),
            dom_evidence=tuple(wire.dom_evidence), model_agreement=wire.agreement,
            provider=self.provider, model=self.model,
        )

    def _http_failure(self, status_code: int, text: str) -> StatusVerificationAssessment:
        lowered = text.lower()
        if status_code == 404 or "model" in lowered and "not found" in lowered:
            code = VerificationFailureCode.MODEL_MISSING
        elif "vision" in lowered or "image" in lowered and "support" in lowered:
            code = VerificationFailureCode.VISION_UNSUPPORTED
        else:
            code = VerificationFailureCode.UNAVAILABLE
        return self._failure(code, f"Ollama HTTP error {status_code}")

    def _failure(self, code: VerificationFailureCode, reason: str) -> StatusVerificationAssessment:
        return StatusVerificationAssessment(
            status=None, confidence=0.0, reasoning=reason, failure_code=code,
            provider=self.provider, model=self.model,
        )

    def _health(self, reachable: bool, vision: bool | None, reason: str) -> StatusVerifierHealth:
        return StatusVerifierHealth(True, self.provider, self.model, True, reachable, vision, reason)

    @staticmethod
    def _validate_local_base_url(base_url: str) -> str:
        parsed = urlparse(base_url.strip())
        if parsed.scheme not in {"http", "https"} or parsed.hostname not in {"127.0.0.1", "localhost", "::1"}:
            raise ValueError("OLLAMA_BASE_URL must use a loopback host")
        if parsed.username or parsed.password or parsed.query or parsed.fragment or parsed.path not in {"", "/"}:
            raise ValueError("OLLAMA_BASE_URL must not contain credentials, path, query, or fragment")
        return base_url.strip().rstrip("/")
