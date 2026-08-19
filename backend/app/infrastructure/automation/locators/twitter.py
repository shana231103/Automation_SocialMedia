# File: backend/app/infrastructure/automation/locators/twitter.py
"""Deterministic X locator candidates grouped by semantic intent."""

from types import MappingProxyType
from typing import Mapping

from app.infrastructure.automation.semantic_types import LocatorSpec, SemanticIntent


TWITTER_LOCATORS: Mapping[SemanticIntent, LocatorSpec] = MappingProxyType({
    SemanticIntent.EMAIL_OR_PHONE_INPUT: LocatorSpec(
        hint_text="X username, email, or phone input",
        selectors=(
            "css:input[name='text']",
            "css:input[autocomplete='username']",
            "css:input[type='text']",
        ),
        timeout_seconds=2.0,
    ),
    SemanticIntent.PASSWORD_INPUT: LocatorSpec(
        hint_text="X password input",
        selectors=("css:input[name='password']",),
        timeout_seconds=2.0,
    ),
    SemanticIntent.CONTINUE_CONTROL: LocatorSpec(
        hint_text="X next or continue control",
        selectors=(
            "css:button[data-testid='ocfEnterTextNextButton']",
            "xpath://button[.//span[text()='Next']]",
            "xpath://button[.//span[text()='Tiếp theo']]",
        ),
        timeout_seconds=3.0,
    ),
    SemanticIntent.LOGIN_SUBMIT_CONTROL: LocatorSpec(
        hint_text="X login or submit control",
        selectors=(
            "css:button[data-testid='LoginForm_Login_Button']",
            "xpath://button[.//span[text()='Log in']]",
            "xpath://button[.//span[text()='Đăng nhập']]",
        ),
        timeout_seconds=3.0,
    ),
})
