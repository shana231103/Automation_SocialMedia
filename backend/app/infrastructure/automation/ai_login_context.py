# File: backend/app/infrastructure/automation/ai_login_context.py
"""Request-scoped budgets, terminal reuse, and safe AI metrics."""

from __future__ import annotations

from dataclasses import dataclass
import threading
import time

from app.application.ai_login import AICapability, AIFailureCode, AIUsage, TerminalAssessment
from app.infrastructure.ai.config import AILimits


@dataclass(frozen=True)
class BudgetReservation:
    granted: bool
    failure_code: AIFailureCode | None
    _semaphore: threading.BoundedSemaphore | None = None

    def release(self) -> None:
        if self.granted and self._semaphore is not None:
            self._semaphore.release()


@dataclass(frozen=True)
class AISessionMetrics:
    calls: int
    duration_ms: int
    input_tokens: int
    output_tokens: int
    terminal_reuse_hits: int


class AILoginContext:
    def __init__(self, limits: AILimits, process_limiter: threading.BoundedSemaphore,
                 cancellation_event: threading.Event | None = None) -> None:
        self.limits = limits
        self._limiter = process_limiter
        self._cancel = cancellation_event
        self._started = time.monotonic()
        self._lock = threading.Lock()
        self._calls = 0
        self._input_tokens = self._output_tokens = self._reuse_hits = 0
        self._terminal: dict[str, TerminalAssessment] = {}

    def reserve_call(self, capability: AICapability) -> BudgetReservation:
        del capability
        with self._lock:
            if self.cancelled():
                return BudgetReservation(False, AIFailureCode.CANCELLED)
            if self._calls >= self.limits.max_calls_per_login or self.remaining_seconds() <= 0:
                return BudgetReservation(False, AIFailureCode.BUDGET_EXHAUSTED)
        if not self._limiter.acquire(timeout=max(0.01, min(1.0, self.remaining_seconds()))):
            return BudgetReservation(False, AIFailureCode.BUDGET_EXHAUSTED)
        with self._lock:
            if (self.cancelled() or self._calls >= self.limits.max_calls_per_login
                    or self.remaining_seconds() <= 0):
                self._limiter.release()
                code = AIFailureCode.CANCELLED if self.cancelled() else AIFailureCode.BUDGET_EXHAUSTED
                return BudgetReservation(False, code)
            self._calls += 1
        return BudgetReservation(True, None, self._limiter)

    def remaining_seconds(self) -> float:
        return self.limits.session_timeout - (time.monotonic() - self._started)

    def cancelled(self) -> bool:
        return bool(self._cancel and self._cancel.is_set())

    def record_usage(self, usage: AIUsage) -> None:
        with self._lock:
            self._input_tokens += max(0, usage.input_tokens)
            self._output_tokens += max(0, usage.output_tokens)

    def remember_terminal(self, observation_id: str, assessment: TerminalAssessment) -> None:
        if observation_id and assessment.observation_id == observation_id:
            with self._lock:
                self._terminal = {observation_id: assessment}

    def matching_terminal(self, observation_id: str) -> TerminalAssessment | None:
        with self._lock:
            found = self._terminal.get(observation_id)
            if found is not None:
                self._reuse_hits += 1
            return found

    def snapshot_metrics(self) -> AISessionMetrics:
        with self._lock:
            return AISessionMetrics(self._calls,
                                    int((time.monotonic() - self._started) * 1000),
                                    self._input_tokens, self._output_tokens, self._reuse_hits)


class AILoginContextFactory:
    def __init__(self, limits: AILimits) -> None:
        self.limits = limits
        self._limiter = threading.BoundedSemaphore(limits.max_concurrent_requests)

    def create(self, cancellation_event: threading.Event | None = None) -> AILoginContext:
        return AILoginContext(self.limits, self._limiter, cancellation_event)
