# File: backend/app/application/status_verification.py
"""Compatibility exports for the provider-neutral AI login contracts."""

from app.application.ai_login import (
    AIFailureCode,
    AIProviderHealth,
    ProtectedObservation,
    StatusVerificationDecision,
    TerminalAssessment,
    TerminalAssessmentPort,
    VerificationOutcome,
)

VerificationFailureCode = AIFailureCode
StatusVerificationEvidence = ProtectedObservation
StatusVerificationAssessment = TerminalAssessment
StatusVerifierHealth = AIProviderHealth
AccountStatusVerifier = TerminalAssessmentPort

__all__ = [
    "AccountStatusVerifier",
    "StatusVerificationAssessment",
    "StatusVerificationDecision",
    "StatusVerificationEvidence",
    "StatusVerifierHealth",
    "VerificationFailureCode",
    "VerificationOutcome",
]
