# File: backend/app/infrastructure/automation/locators/tiktok.py
"""Deterministic TikTok locator candidates grouped by semantic intent."""

from types import MappingProxyType
from typing import Mapping

from app.infrastructure.automation.semantic_types import LocatorSpec, SemanticIntent


TIKTOK_LOCATORS: Mapping[SemanticIntent, LocatorSpec] = MappingProxyType({
    SemanticIntent.EMAIL_OR_PHONE_INPUT: LocatorSpec(
        hint_text="TikTok email or username input",
        selectors=("css:input[name='username']",),
        timeout_seconds=5.0,
    ),
    SemanticIntent.PASSWORD_INPUT: LocatorSpec(
        hint_text="TikTok password input",
        selectors=("css:input[type='password']",),
        timeout_seconds=5.0,
    ),
    SemanticIntent.LOGIN_SUBMIT_CONTROL: LocatorSpec(
        hint_text="TikTok login or submit control",
        selectors=("css:button[type='submit']",),
        timeout_seconds=2.0,
    ),
})
