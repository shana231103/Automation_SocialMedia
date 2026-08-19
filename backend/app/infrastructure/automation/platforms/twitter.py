"""Driver-agnostic X (Twitter) login automation script."""

from __future__ import annotations

import threading
from typing import Any, Callable, Dict, Generator

from app.domain.models import LoginStatus, Platform
from app.infrastructure.automation.page_wrapper import AutomationPage
from app.infrastructure.automation.platforms._helpers import (
    host_and_path, semantic_candidate_visible, semantic_resolution_message, wait_or_cancel,
)
from app.infrastructure.automation.semantic_types import ResolutionFailure, SemanticIntent


def _is_x_authenticated(page: AutomationPage, url: str) -> bool:
    host, path = host_and_path(url)
    return bool(
        page.find("css:[data-testid='AppTabBar_Home_Link']", timeout=0.1)
        or (host in {"x.com", "www.x.com"} and path == "/home")
    )


def _requires_x_checkpoint(page: AutomationPage, url: str) -> bool:
    lowered_url = url.lower()
    return bool(
        "checkpoint" in lowered_url
        or "challenge" in lowered_url
        or page.find("text:Authenticate your account", timeout=0.1)
        or page.find("text:Verify your identity", timeout=0.1)
    )


def _is_x_dead(page: AutomationPage, url: str) -> bool:
    lowered_url = url.lower()
    return bool(
        "account-suspended" in lowered_url
        or page.find("text:Account suspended", timeout=0.1)
        or page.find("text:Your account is suspended", timeout=0.1)
    )


def _has_x_login_error(page: AutomationPage) -> bool:
    return bool(
        page.find("text:Wrong password", timeout=0.1)
        or page.find("text:Incorrect password", timeout=0.1)
        or page.find("text:We could not authenticate you", timeout=0.1)
    )


def _wait_for_x_password_or_confirmation(
    page: AutomationPage,
    cancellation_event: threading.Event | None,
) -> str:
    for _ in range(16):
        if page.find("css:input[data-testid='ocfEnterTextTextInput']", timeout=0.1):
            return "confirmation"
        if _requires_x_checkpoint(page, page.url):
            return "checkpoint"
        if _is_x_dead(page, page.url):
            return "dead"
        if semantic_candidate_visible(page, Platform.TWITTER, SemanticIntent.PASSWORD_INPUT):
            return "ready"
        if wait_or_cancel(0.5, cancellation_event):
            return "cancelled"
    return "timeout"


def login_twitter(
    page: AutomationPage,
    username: str,
    password: str,
    log_func: Callable[[str], Dict[str, Any]],
    cancellation_event: threading.Event | None = None,
) -> Generator[Dict[str, Any], None, LoginStatus]:
    yield log_func("Opening X login...")
    page.goto("https://x.com/i/flow/login")
    if _is_x_authenticated(page, page.url):
        yield log_func("An existing X session was detected.")
        return LoginStatus.LOGGED_IN

    for _ in range(16):
        if semantic_candidate_visible(
            page, Platform.TWITTER, SemanticIntent.EMAIL_OR_PHONE_INPUT,
        ):
            break
        if wait_or_cancel(0.5, cancellation_event):
            yield log_func("X login was cancelled.")
            return LoginStatus.LOGGED_OUT

    username_intents = (
        SemanticIntent.EMAIL_OR_PHONE_INPUT,
        SemanticIntent.CONTINUE_CONTROL,
    )
    username_results = page.find_semantic_many(
        Platform.TWITTER, username_intents, cancellation_event,
    )
    username_resolution = username_results[SemanticIntent.EMAIL_OR_PHONE_INPUT]
    continue_resolution = username_results[SemanticIntent.CONTINUE_CONTROL]
    for label, resolution in (
        ("username or email input", username_resolution),
        ("continue control", continue_resolution),
    ):
        yield log_func(semantic_resolution_message("X", label, resolution))
        if resolution.failure == ResolutionFailure.CANCELLED:
            yield log_func("X login was cancelled.")
            return LoginStatus.LOGGED_OUT

    username_input = username_resolution.element
    if not username_input:
        yield log_func("X username input was not found.")
        return LoginStatus.LOGGED_OUT

    username_input.input(username)
    if wait_or_cancel(0.5, cancellation_event):
        yield log_func("X login was cancelled.")
        return LoginStatus.LOGGED_OUT
    next_btn = continue_resolution.element
    if next_btn:
        next_btn.click()
    else:
        yield log_func("X continue control was not resolved; submitting by keyboard.")
        username_input.press("Enter")

    stage = _wait_for_x_password_or_confirmation(page, cancellation_event)
    if stage == "cancelled":
        yield log_func("X login was cancelled.")
        return LoginStatus.LOGGED_OUT
    if stage == "confirmation":
        yield log_func("X requires an email or phone verification step.")
        return LoginStatus.CHECKPOINT
    if stage == "checkpoint":
        yield log_func("X requires CAPTCHA or a security verification.")
        return LoginStatus.CHECKPOINT
    if stage == "dead":
        yield log_func("X reports that the account is suspended.")
        return LoginStatus.DEAD

    password_intents = (
        SemanticIntent.PASSWORD_INPUT,
        SemanticIntent.LOGIN_SUBMIT_CONTROL,
    )
    password_results = page.find_semantic_many(
        Platform.TWITTER, password_intents, cancellation_event,
    )
    pass_resolution = password_results[SemanticIntent.PASSWORD_INPUT]
    submit_resolution = password_results[SemanticIntent.LOGIN_SUBMIT_CONTROL]
    for label, resolution in (
        ("password input", pass_resolution),
        ("submit control", submit_resolution),
    ):
        yield log_func(semantic_resolution_message("X", label, resolution))
        if resolution.failure == ResolutionFailure.CANCELLED:
            yield log_func("X login was cancelled.")
            return LoginStatus.LOGGED_OUT

    pass_input = pass_resolution.element
    if not pass_input:
        yield log_func("X password input was not found.")
        return LoginStatus.LOGGED_OUT

    pass_input.input(password)
    if wait_or_cancel(0.5, cancellation_event):
        yield log_func("X login was cancelled.")
        return LoginStatus.LOGGED_OUT
    login_btn = submit_resolution.element
    if login_btn:
        login_btn.click()
    else:
        yield log_func("X submit control was not resolved; submitting by keyboard.")
        pass_input.press("Enter")

    for _ in range(20):
        if wait_or_cancel(0.5, cancellation_event):
            yield log_func("X login was cancelled.")
            return LoginStatus.LOGGED_OUT
        url = page.url
        if _is_x_authenticated(page, url):
            yield log_func("X login succeeded.")
            return LoginStatus.LOGGED_IN
        if _is_x_dead(page, url):
            yield log_func("X reports that the account is suspended.")
            return LoginStatus.DEAD
        if _requires_x_checkpoint(page, url):
            yield log_func("X requires CAPTCHA or a security verification.")
            return LoginStatus.CHECKPOINT
        if _has_x_login_error(page):
            yield log_func("X rejected the login credentials or request.")
            return LoginStatus.LOGGED_OUT

    yield log_func("X login did not reach a conclusive state before the timeout.")
    return LoginStatus.LOGGED_OUT
