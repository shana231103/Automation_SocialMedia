# File: backend/app/infrastructure/automation/locators/youtube.py
"""Deterministic Google/YouTube locator candidates grouped by semantic intent."""

from types import MappingProxyType
from typing import Mapping

from app.infrastructure.automation.semantic_types import LocatorSpec, SemanticIntent


YOUTUBE_LOCATORS: Mapping[SemanticIntent, LocatorSpec] = MappingProxyType({
    SemanticIntent.EMAIL_OR_PHONE_INPUT: LocatorSpec(
        hint_text="Google email or phone input",
        selectors=("css:input[type='email']", "#identifierId"),
        timeout_seconds=5.0,
    ),
    SemanticIntent.PASSWORD_INPUT: LocatorSpec(
        hint_text="Google password input",
        selectors=("css:input[type='password']",),
        timeout_seconds=2.0,
    ),
    SemanticIntent.CONTINUE_CONTROL: LocatorSpec(
        hint_text="Google identifier next or continue control",
        selectors=(
            "css:#identifierNext",
            "xpath://button[.//span[text()='Next']]",
            "xpath://button[.//span[text()='Tiếp theo']]",
        ),
        timeout_seconds=3.0,
    ),
    SemanticIntent.LOGIN_SUBMIT_CONTROL: LocatorSpec(
        hint_text="Google password next or sign-in control",
        selectors=(
            "css:#passwordNext",
            "xpath://button[.//span[text()='Next']]",
            "xpath://button[.//span[text()='Tiếp theo']]",
        ),
        timeout_seconds=3.0,
    ),
})
