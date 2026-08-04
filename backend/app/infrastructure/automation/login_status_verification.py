# File: backend/app/infrastructure/automation/login_status_verification.py
"""Capture evidence and resolve advisory AI login-status assessments safely."""

import base64
import os
import re
import threading
import time

from app.application.status_verification import (
    AccountStatusVerifier,
    StatusVerificationAssessment,
    StatusVerificationDecision,
    StatusVerificationEvidence,
    StatusVerifierHealth,
    VerificationOutcome,
)
from app.domain.models import LoginStatus, Platform
from app.infrastructure.ai.dom_parser import DOMParser
from app.infrastructure.automation.login_status_policy import may_upgrade_to_logged_in, sanitize_url
from app.infrastructure.automation.page_wrapper import AutomationPage


class LoginStatusVerificationCoordinator:
    """Gate evidence capture and apply deterministic status conflict policy."""

    def __init__(
        self,
        verifier: AccountStatusVerifier,
        enabled: bool = True,
        confidence_threshold: float = 0.80,
        login_upgrade_threshold: float = 0.95,
        max_dom_chars: int = 6000,
        max_screenshot_bytes: int = 4194304,
        disabled_reason: str = "",
    ) -> None:
        if not 0 <= confidence_threshold <= login_upgrade_threshold <= 1:
            raise ValueError("Invalid AI status confidence thresholds")
        if not 1000 <= max_dom_chars <= 12000 or not 65536 <= max_screenshot_bytes <= 8388608:
            raise ValueError("Invalid AI status evidence limits")
        self.verifier = verifier
        self.enabled = enabled
        self.confidence_threshold = confidence_threshold
        self.login_upgrade_threshold = login_upgrade_threshold
        self.max_dom_chars = max_dom_chars
        self.max_screenshot_bytes = max_screenshot_bytes
        self.disabled_reason = disabled_reason

        self.provider = str(getattr(verifier, "provider", "ollama"))
        self.model = str(getattr(verifier, "model", ""))
    @classmethod
    def from_env(cls) -> "LoginStatusVerificationCoordinator":
        from app.infrastructure.ai.ollama_status_verifier import OllamaStatusVerifier

        try:
            enabled = cls._parse_bool(os.getenv("ENABLE_AI_STATUS_VERIFICATION", "true"))
            return cls(
                verifier=OllamaStatusVerifier.from_env(), enabled=enabled,
                confidence_threshold=float(os.getenv("AI_STATUS_CONFIDENCE_THRESHOLD", "0.80")),
                login_upgrade_threshold=float(os.getenv("AI_STATUS_LOGIN_CONFIDENCE_THRESHOLD", "0.95")),
                max_dom_chars=int(os.getenv("AI_STATUS_MAX_DOM_CHARS", "6000")),
                max_screenshot_bytes=int(os.getenv("AI_STATUS_MAX_SCREENSHOT_BYTES", "4194304")),
                disabled_reason="Disabled by configuration" if not enabled else "",
            )
        except (TypeError, ValueError):
            return cls(OllamaStatusVerifier(), enabled=False, disabled_reason="Invalid AI status configuration")

    def should_verify(
        self,
        preliminary_status: LoginStatus,
        cancellation_event: threading.Event | None,
    ) -> bool:
        return (
            self.enabled
            and preliminary_status != LoginStatus.LOGGED_IN
            and not (cancellation_event and cancellation_event.is_set())
        )

    def resolve(
        self,
        page: AutomationPage,
        platform: Platform,
        preliminary_status: LoginStatus,
        secrets: tuple[str, ...] = (),
        cancellation_event: threading.Event | None = None,
    ) -> StatusVerificationDecision:
        started = time.perf_counter()
        if cancellation_event and cancellation_event.is_set():
            return self._fallback(preliminary_status, VerificationOutcome.CANCELLED, "Verification cancelled", 0)
        try:
            evidence = self._build_evidence(page, platform, preliminary_status, secrets)
        except (RuntimeError, ValueError, TypeError):
            return self._fallback(preliminary_status, VerificationOutcome.FALLBACK, "Evidence capture failed", self._elapsed(started))
        if cancellation_event and cancellation_event.is_set():
            return self._fallback(preliminary_status, VerificationOutcome.CANCELLED, "Verification cancelled", self._elapsed(started))
        try:
            assessment = self.verifier.verify(evidence, cancellation_event)
        except Exception:
            return self._fallback(preliminary_status, VerificationOutcome.FALLBACK, "Verifier failed", self._elapsed(started))
        if cancellation_event and cancellation_event.is_set():
            return self._fallback(preliminary_status, VerificationOutcome.CANCELLED, "Verification cancelled", self._elapsed(started), assessment, secrets)
        return self._resolve_assessment(evidence, assessment, self._elapsed(started), secrets)

    def get_status(self) -> StatusVerifierHealth:
        if self.enabled:
            return self.verifier.get_status()
        configured = self.disabled_reason != "Invalid AI status configuration"
        return StatusVerifierHealth(
            False, self.provider, self.model, configured, None, None, self.disabled_reason,
        )

    def _build_evidence(
        self, page: AutomationPage, platform: Platform, preliminary_status: LoginStatus,
        secrets: tuple[str, ...],
    ) -> StatusVerificationEvidence:
        screenshot = page.capture_screenshot_base64(mask_sensitive=True)
        image_bytes = base64.b64decode(screenshot, validate=True)
        if not image_bytes or len(image_bytes) > self.max_screenshot_bytes:
            raise ValueError("Screenshot is empty or too large")
        dom = DOMParser.extract_status_snippet(page.html, self.max_dom_chars, secrets)
        if not dom:
            raise ValueError("DOM evidence is empty")
        return StatusVerificationEvidence(
            platform, preliminary_status, sanitize_url(page.url), screenshot, dom,
        )

    def _resolve_assessment(
        self, evidence: StatusVerificationEvidence, assessment: StatusVerificationAssessment,
        duration_ms: int, secrets: tuple[str, ...],
    ) -> StatusVerificationDecision:
        reason = self._sanitize_text(assessment.reasoning, secrets)
        if assessment.failure_code or assessment.status is None:
            return self._fallback(
                evidence.preliminary_status, VerificationOutcome.FALLBACK, reason,
                duration_ms, assessment, secrets,
            )
        if assessment.confidence < self.confidence_threshold:
            detail = f"AI confidence below threshold ({assessment.confidence:.2f} < {self.confidence_threshold:.2f}). {reason}"
            return self._fallback(
                evidence.preliminary_status, VerificationOutcome.REJECTED, detail,
                duration_ms, assessment, secrets,
            )
        if assessment.status == evidence.preliminary_status:
            outcome, final = VerificationOutcome.CONFIRMED, evidence.preliminary_status
        elif assessment.status != LoginStatus.LOGGED_IN:
            outcome, final = VerificationOutcome.OVERRIDDEN, assessment.status
        elif may_upgrade_to_logged_in(evidence, assessment, self.login_upgrade_threshold):
            outcome, final = VerificationOutcome.OVERRIDDEN, LoginStatus.LOGGED_IN
        else:
            outcome, final = VerificationOutcome.REJECTED, evidence.preliminary_status
            reason = f"Logged-in upgrade guard rejected the assessment. {reason}"
        visual, dom = self._safe_evidence(assessment, secrets)
        return StatusVerificationDecision(
            evidence.preliminary_status, final, assessment.status, assessment.confidence,
            outcome, reason[:240], duration_ms, assessment.provider, assessment.model,
            visual, dom, assessment.model_agreement, assessment.failure_code,
        )

    def _fallback(
        self, preliminary: LoginStatus, outcome: VerificationOutcome, reason: str,
        duration_ms: int, assessment: StatusVerificationAssessment | None = None,
        secrets: tuple[str, ...] = (),
    ) -> StatusVerificationDecision:
        visual, dom = self._safe_evidence(assessment, secrets) if assessment else ((), ())
        return StatusVerificationDecision(
            preliminary, preliminary, assessment.status if assessment else None,
            assessment.confidence if assessment else None, outcome,
            self._sanitize_text(reason, secrets), duration_ms,
            assessment.provider if assessment else "ollama", assessment.model if assessment else "",
            visual, dom, assessment.model_agreement if assessment else None,
            assessment.failure_code if assessment else None,
        )

    def _safe_evidence(
        self, assessment: StatusVerificationAssessment, secrets: tuple[str, ...],
    ) -> tuple[tuple[str, ...], tuple[str, ...]]:
        visual = tuple(self._sanitize_text(item, secrets) for item in assessment.visual_evidence[:3])
        dom = tuple(self._sanitize_text(item, secrets) for item in assessment.dom_evidence[:3])
        return visual, dom

    @staticmethod
    def _sanitize_text(text: str, secrets: tuple[str, ...]) -> str:
        clean = re.sub(r"[\x00-\x1f\x7f]", " ", text)
        for secret in sorted((item for item in secrets if item), key=len, reverse=True):
            clean = clean.replace(secret, "[redacted]")
        return clean[:240]

    @staticmethod
    def _parse_bool(value: str) -> bool:
        normalized = value.strip().lower()
        if normalized in {"true", "1", "yes"}:
            return True
        if normalized in {"false", "0", "no"}:
            return False
        raise ValueError("Invalid boolean")

    @staticmethod
    def _elapsed(started: float) -> int:
        return int((time.perf_counter() - started) * 1000)
