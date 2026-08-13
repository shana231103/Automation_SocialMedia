# File: backend/app/infrastructure/automation/login_status_verification.py
"""Backward-compatible import for the unified terminal status coordinator."""

from app.infrastructure.automation.terminal_status_coordinator import TerminalStatusCoordinator

LoginStatusVerificationCoordinator = TerminalStatusCoordinator

__all__ = ["LoginStatusVerificationCoordinator", "TerminalStatusCoordinator"]
