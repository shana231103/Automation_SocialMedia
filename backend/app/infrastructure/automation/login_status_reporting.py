# File: backend/app/infrastructure/automation/login_status_reporting.py
"""Secret-safe user-facing reporting for terminal AI decisions."""

from app.application.status_verification import StatusVerificationDecision


def decision_to_event_metadata(decision: StatusVerificationDecision) -> dict[str, object]:
    """Serialize bounded diagnostics without raw screenshot, DOM, URL, or evidence text."""
    return {
        "outcome": decision.outcome.value,
        "preliminary_status": decision.preliminary_status.value,
        "final_status": decision.final_status.value,
        "ai_status": decision.ai_status.value if decision.ai_status else None,
        "confidence": decision.confidence,
        "provider": decision.provider,
        "model": decision.model,
        "duration_ms": decision.duration_ms,
        "reason": decision.reason,
        "visual_evidence_count": len(decision.visual_evidence),
        "dom_evidence_count": len(decision.dom_evidence),
        "model_agreement": decision.model_agreement,
        "failure_code": decision.failure_code.value if decision.failure_code else None,
    }


def decision_to_log_message(decision: StatusVerificationDecision) -> str:
    """Explain the policy outcome while exposing only evidence counts."""
    ai_status = decision.ai_status.value if decision.ai_status else "no AI result"
    confidence = f"{decision.confidence:.0%}" if decision.confidence is not None else "unknown"
    evidence = (f"{len(decision.visual_evidence)} visual / "
                f"{len(decision.dom_evidence)} DOM signals")
    failure = f" | failure={decision.failure_code.value}" if decision.failure_code else ""
    return (
        f"AI terminal assessment {decision.outcome.value}: "
        f"{decision.preliminary_status.value} -> {decision.final_status.value} "
        f"({decision.duration_ms} ms) | AI={ai_status} | confidence={confidence} | "
        f"reason={decision.reason or 'not provided'} | evidence={evidence}{failure}"
    )
