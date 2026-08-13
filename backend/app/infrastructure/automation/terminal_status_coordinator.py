# File: backend/app/infrastructure/automation/terminal_status_coordinator.py
"""Protected terminal evidence, exact-observation reuse, and final status policy."""

from dataclasses import replace
import re
import threading
import time

from app.application.ai_login import (
    AICapability, AIFailureCode, StatusVerificationDecision, TerminalAssessment,
    TerminalAssessmentPort, VerificationOutcome,
)
from app.domain.models import LoginStatus, Platform
from app.infrastructure.ai.status_policy import hard_evidence_status
from app.infrastructure.automation.ai_login_context import AILoginContext
from app.infrastructure.automation.login_status_policy import may_upgrade_to_logged_in
from app.infrastructure.automation.page_wrapper import AutomationPage
from app.infrastructure.automation.protected_observation import capture_protected_observation


class TerminalStatusCoordinator:
    def __init__(self, terminal_port: TerminalAssessmentPort | None,
                 ai_context: AILoginContext, confidence_threshold: float = 0.80,
                 login_upgrade_threshold: float = 0.95) -> None:
        if not 0 <= confidence_threshold <= login_upgrade_threshold <= 1:
            raise ValueError("Invalid AI status confidence thresholds")
        self.terminal_port = terminal_port
        self.ai_context = ai_context
        self.confidence_threshold = confidence_threshold
        self.login_upgrade_threshold = login_upgrade_threshold

    def should_verify(self, preliminary_status: LoginStatus,
                      cancellation_event: threading.Event | None) -> bool:
        return (self.terminal_port is not None and preliminary_status is not LoginStatus.LOGGED_IN
                and not (cancellation_event and cancellation_event.is_set()))

    def resolve(self, page: AutomationPage, platform: Platform,
                preliminary_status: LoginStatus, secrets: tuple[str, ...] = (),
                cancellation_event: threading.Event | None = None) -> StatusVerificationDecision:
        started = time.perf_counter()
        if cancellation_event and cancellation_event.is_set():
            return self._fallback(preliminary_status, VerificationOutcome.CANCELLED,
                                  "Terminal assessment cancelled", 0, AIFailureCode.CANCELLED)
        if preliminary_status is LoginStatus.LOGGED_IN:
            return self._fallback(preliminary_status, VerificationOutcome.SKIPPED_LOGGED_IN,
                                  "Deterministic login success; AI was not called", 0)
        try:
            observation = capture_protected_observation(
                page, platform, preliminary_status, secrets, self.ai_context.limits.max_dom_chars,
                self.ai_context.limits.max_screenshot_bytes)
        except (TypeError, ValueError, RuntimeError):
            return self._fallback(preliminary_status, VerificationOutcome.FALLBACK,
                                  "Protected terminal evidence capture failed", self._elapsed(started),
                                  AIFailureCode.PAYLOAD_TOO_LARGE)
        cached = self.ai_context.matching_terminal(observation.observation_id)
        if cached is not None:
            return self._resolve_assessment(observation, cached, self._elapsed(started),
                                            secrets, VerificationOutcome.REUSED)
        if self.terminal_port is None:
            return self._fallback(preliminary_status, VerificationOutcome.SKIPPED_DISABLED,
                                  "Remote terminal assessment is disabled", self._elapsed(started),
                                  AIFailureCode.DISABLED)
        reservation = self.ai_context.reserve_call(AICapability.TERMINAL_ASSESSMENT)
        if not reservation.granted:
            return self._fallback(preliminary_status, VerificationOutcome.FALLBACK,
                                  "Terminal call budget is unavailable", self._elapsed(started),
                                  reservation.failure_code)
        try:
            assessment = self.terminal_port.assess_terminal(
                observation, preliminary_status, cancellation_event)
            self.ai_context.record_usage(assessment.usage)
        except Exception:
            return self._fallback(preliminary_status, VerificationOutcome.FALLBACK,
                                  "Terminal provider failed", self._elapsed(started),
                                  AIFailureCode.UNAVAILABLE)
        finally:
            reservation.release()
        assessment = self._apply_hard_evidence(observation, assessment)
        self.ai_context.remember_terminal(observation.observation_id, assessment)
        return self._resolve_assessment(observation, assessment, self._elapsed(started), secrets)

    @staticmethod
    def _apply_hard_evidence(observation, assessment: TerminalAssessment) -> TerminalAssessment:
        hard = hard_evidence_status(observation)
        if hard is None or assessment.status is hard:
            return assessment
        return replace(
            assessment, status=hard,
            reason=("Deterministic URL/DOM evidence corrected the advisory status to checkpoint. "
                    + assessment.reason)[:500])

    def _resolve_assessment(self, observation, assessment: TerminalAssessment,
                            duration_ms: int, secrets: tuple[str, ...],
                            accepted_outcome: VerificationOutcome | None = None) -> StatusVerificationDecision:
        preliminary = observation.preliminary_status or LoginStatus.LOGGED_OUT
        reason = self._sanitize(assessment.reason, secrets)
        if assessment.failure_code or assessment.status is None:
            return self._fallback(preliminary, VerificationOutcome.FALLBACK, reason, duration_ms,
                                  assessment.failure_code, assessment)
        if assessment.confidence < self.confidence_threshold:
            return self._fallback(preliminary, VerificationOutcome.REJECTED,
                                  f"AI confidence below threshold. {reason}", duration_ms,
                                  None, assessment)
        if assessment.status is preliminary:
            outcome, final = accepted_outcome or VerificationOutcome.CONFIRMED, preliminary
        elif assessment.status is not LoginStatus.LOGGED_IN:
            outcome, final = accepted_outcome or VerificationOutcome.OVERRIDDEN, assessment.status
        elif may_upgrade_to_logged_in(observation, assessment, self.login_upgrade_threshold):
            outcome, final = accepted_outcome or VerificationOutcome.OVERRIDDEN, LoginStatus.LOGGED_IN
        else:
            outcome, final = VerificationOutcome.REJECTED, preliminary
            reason = f"Logged-in upgrade guard rejected the assessment. {reason}"
        visual = tuple(self._sanitize(item, secrets) for item in assessment.visual_evidence)[:5]
        dom = tuple(self._sanitize(item, secrets) for item in assessment.dom_evidence)[:5]
        return StatusVerificationDecision(preliminary, final, assessment.status,
                                          assessment.confidence, outcome, reason[:240], duration_ms,
                                          assessment.provider, assessment.model, visual, dom,
                                          assessment.model_agreement, assessment.failure_code)

    def _fallback(self, preliminary: LoginStatus, outcome: VerificationOutcome, reason: str,
                  duration_ms: int, failure: AIFailureCode | None = None,
                  assessment: TerminalAssessment | None = None) -> StatusVerificationDecision:
        return StatusVerificationDecision(
            preliminary, preliminary, assessment.status if assessment else None,
            assessment.confidence if assessment else None, outcome, reason[:240], duration_ms,
            assessment.provider if assessment else "disabled", assessment.model if assessment else "",
            failure_code=failure or (assessment.failure_code if assessment else None))

    @staticmethod
    def _sanitize(text: str, secrets: tuple[str, ...]) -> str:
        safe = re.sub(r"[\r\n\t]+", " ", str(text))
        safe = re.sub(r"https?://\S+", "[redacted-url]", safe, flags=re.IGNORECASE)
        for secret in secrets:
            if secret:
                safe = safe.replace(secret, "[redacted]")
        return safe[:240]

    @staticmethod
    def _elapsed(started: float) -> int:
        return int((time.perf_counter() - started) * 1000)
