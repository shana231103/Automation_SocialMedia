# File: backend/app/infrastructure/automation/login_status_reporting.py
"""Safe user-facing reporting for AI login-status decisions."""

from app.application.status_verification import StatusVerificationDecision


def decision_to_event_metadata(decision: StatusVerificationDecision) -> dict[str, object]:
    """Serialize bounded diagnostic fields without raw screenshot or DOM payloads."""
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
        "visual_evidence": list(decision.visual_evidence),
        "dom_evidence": list(decision.dom_evidence),
        "model_agreement": decision.model_agreement,
        "failure_code": decision.failure_code.value if decision.failure_code else None,
    }


def decision_to_log_message(decision: StatusVerificationDecision) -> str:
    """Explain what AI saw and why the deterministic policy chose the final state."""
    ai_status = decision.ai_status.value if decision.ai_status else "không có kết quả"
    confidence = f"{decision.confidence:.0%}" if decision.confidence is not None else "không có"
    visual = "; ".join(decision.visual_evidence) or "không có bằng chứng hình ảnh"
    dom = "; ".join(decision.dom_evidence) or "không có bằng chứng DOM"
    failure = f" | Mã lỗi: {decision.failure_code.value}" if decision.failure_code else ""
    return (
        f"AI status verification {decision.outcome.value}: "
        f"{decision.preliminary_status.value} -> {decision.final_status.value} "
        f"({decision.duration_ms} ms) | AI dự đoán: {ai_status} | "
        f"Độ tin cậy: {confidence} | Lý do: {decision.reason or 'không được cung cấp'} | "
        f"Thấy trên ảnh: {visual} | Thấy trong DOM: {dom}{failure}"
    )
