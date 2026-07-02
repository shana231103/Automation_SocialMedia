# File: backend/app/infrastructure/automation/actions/__init__.py
"""
Registry for mapping browser automation action names to their concrete action classes.
"""

from typing import Type
from app.infrastructure.automation.actions.action_base import AutomationAction
from app.infrastructure.automation.actions.login_action import LoginAction

# Central registry mapping action names to action implementation classes.
# To register a new action, simply add it to this dictionary.
ACTION_REGISTRY: dict[str, Type[AutomationAction]] = {
    "login": LoginAction
}

__all__ = [
    "AutomationAction",
    "LoginAction",
    "ACTION_REGISTRY",
]
