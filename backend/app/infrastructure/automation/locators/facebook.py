# File: backend/app/infrastructure/automation/locators/facebook.py
"""Deterministic Facebook locator candidates grouped by semantic intent."""

from types import MappingProxyType
from typing import Mapping

from app.infrastructure.automation.semantic_types import LocatorSpec, SemanticIntent


FACEBOOK_LOCATORS: Mapping[SemanticIntent, LocatorSpec] = MappingProxyType({
    SemanticIntent.EMAIL_OR_PHONE_INPUT: LocatorSpec(
        hint_text="Facebook email or phone input",
        selectors=("css:input[name='email']", "#email", "css:input[type='email']"),
        timeout_seconds=1.5,
    ),
    SemanticIntent.PASSWORD_INPUT: LocatorSpec(
        hint_text="Facebook password input",
        selectors=("css:input[name='pass']", "#pass", "css:input[type='password']"),
        timeout_seconds=1.5,
    ),
    SemanticIntent.CONTINUE_CONTROL: LocatorSpec(
        hint_text="Facebook continue or next control",
        selectors=("text:Continue", "text:Next", "css:button[type='submit']"),
        timeout_seconds=2.0,
    ),
    SemanticIntent.LOGIN_SUBMIT_CONTROL: LocatorSpec(
        hint_text="Facebook login or submit control",
        selectors=(
            "css:button[name='login']",
            "css:[data-testid='royal_login_button']",
            "css:button[type='submit']",
            "css:input[type='submit']",
        ),
        timeout_seconds=3.0,
    ),
})
