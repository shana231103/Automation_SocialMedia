"""Driver-agnostic Facebook login automation script."""

from __future__ import annotations

import threading
from typing import Any, Callable, Dict, Generator

from app.domain.models import LoginStatus, Platform
from app.infrastructure.automation.page_wrapper import AutomationPage
from app.infrastructure.automation.platforms._helpers import host_and_path, wait_or_cancel
from app.infrastructure.automation.semantic_types import (
    ResolutionFailure, ResolutionSource, SemanticIntent,
)


def _is_facebook_authenticated(page: AutomationPage, url: str) -> bool:
    host, path = host_and_path(url)
    return bool(
        page.find("css:[role='feed']", timeout=0.1)
        or (host in {"facebook.com", "www.facebook.com"} and path == "/home.php")
    )


def _requires_facebook_checkpoint(page: AutomationPage, url: str) -> bool:
    lowered_url = url.lower()
    return bool(
        any(marker in lowered_url for marker in ("checkpoint", "captcha", "challenge"))
        or page.find("css:[id*='captcha']", timeout=0.1)
        or page.find("css:[class*='captcha']", timeout=0.1)
        or page.find("css:iframe[src*='captcha']", timeout=0.1)
    )


def _is_facebook_dead(page: AutomationPage, url: str) -> bool:
    lowered_url = url.lower()
    return bool(
        "disabled" in lowered_url
        or "suspended" in lowered_url
        or page.find("text:Your account has been disabled", timeout=0.1)
        or page.find("text:Your account has been suspended", timeout=0.1)
    )


def _cancelled(cancellation_event: threading.Event | None, seconds: float) -> bool:
    return wait_or_cancel(seconds, cancellation_event)


def _resolution_message(label: str, resolution: Any) -> str:
    if resolution.source == ResolutionSource.AI:
        return f"Facebook {label} resolved by the configured AI provider in {resolution.ai_attempts} attempt(s)."
    if resolution.source == ResolutionSource.REGISTRY:
        if resolution.ai_attempts:
            return f"Facebook {label} resolved by deterministic fallback after AI attempts."
        return f"Facebook {label} resolved by deterministic fallback."
    return f"Facebook {label} was not resolved after {resolution.ai_attempts} AI attempt(s)."


def login_facebook(
    page: AutomationPage,
    username: str,
    password: str,
    log_func: Callable[[str], Dict[str, Any]],
    cancellation_event: threading.Event | None = None,
) -> Generator[Dict[str, Any], None, LoginStatus]:
    yield log_func("Opening Facebook...")
    page.goto("https://www.facebook.com/")

    if _is_facebook_authenticated(page, page.url):
        yield log_func("An existing Facebook session was detected.")
        return LoginStatus.LOGGED_IN

    yield log_func("Entering Facebook credentials...")
    email_resolution = page.find_semantic(
        Platform.FACEBOOK, SemanticIntent.EMAIL_OR_PHONE_INPUT, cancellation_event,
    )
    yield log_func(_resolution_message("email input", email_resolution))
    if email_resolution.failure == ResolutionFailure.CANCELLED:
        yield log_func("Facebook login was cancelled.")
        return LoginStatus.LOGGED_OUT
    password_resolution = page.find_semantic(
        Platform.FACEBOOK, SemanticIntent.PASSWORD_INPUT, cancellation_event,
    )
    yield log_func(_resolution_message("password input", password_resolution))
    if password_resolution.failure == ResolutionFailure.CANCELLED:
        yield log_func("Facebook login was cancelled.")
        return LoginStatus.LOGGED_OUT
    email_input = email_resolution.element
    pass_input = password_resolution.element
    if not email_input or not pass_input:
        yield log_func(
            "Facebook credential inputs could not be resolved; manual intervention is required."
        )
        return LoginStatus.LOGGED_OUT

    email_input.input(username)
    if _cancelled(cancellation_event, 0.5):
        yield log_func("Facebook login was cancelled.")
        return LoginStatus.LOGGED_OUT
    pass_input.input(password)
    if _cancelled(cancellation_event, 0.5):
        yield log_func("Facebook login was cancelled.")
        return LoginStatus.LOGGED_OUT

    submit_resolution = page.find_semantic(
        Platform.FACEBOOK, SemanticIntent.LOGIN_SUBMIT_CONTROL, cancellation_event,
    )
    yield log_func(_resolution_message("submit control", submit_resolution))
    if submit_resolution.failure == ResolutionFailure.CANCELLED:
        yield log_func("Facebook login was cancelled.")
        return LoginStatus.LOGGED_OUT
    login_btn = submit_resolution.element
    try:
        if login_btn:
            login_btn.click()
        else:
            yield log_func("Facebook submit control was not resolved; submitting by keyboard.")
            pass_input.press("Enter")
    except Exception:
        if login_btn:
            try:
                login_btn.click(by_js=True)
            except Exception:
                pass_input.press("Enter")
        else:
            raise

    yield log_func("Waiting for Facebook to respond; solve any CAPTCHA manually if shown.")
    if _cancelled(cancellation_event, 10):
        yield log_func("Facebook login was cancelled.")
        return LoginStatus.LOGGED_OUT

    for _ in range(20):
        if _cancelled(cancellation_event, 0.5):
            yield log_func("Facebook login was cancelled.")
            return LoginStatus.LOGGED_OUT
        url = page.url
        if _requires_facebook_checkpoint(page, url):
            yield log_func("Facebook requires CAPTCHA or a security verification.")
            return LoginStatus.CHECKPOINT
        if _is_facebook_dead(page, url):
            yield log_func("Facebook reports that the account is disabled or suspended.")
            return LoginStatus.DEAD
        if _is_facebook_authenticated(page, url):
            yield log_func("Facebook login succeeded.")
            return LoginStatus.LOGGED_IN
        if (
            "login" in host_and_path(url)[1]
            or "error" in url.lower()
            or page.find("css:.login_error_box", timeout=0.1)
            or page.find("css:[id='error_box']", timeout=0.1)
        ):
            yield log_func("Facebook rejected the login credentials or request.")
            return LoginStatus.LOGGED_OUT

    yield log_func("Facebook login did not reach a conclusive state before the timeout.")
    return LoginStatus.LOGGED_OUT
