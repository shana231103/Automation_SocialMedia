"""Driver-agnostic YouTube/Google login automation script."""

from __future__ import annotations

import threading
from typing import Any, Callable, Dict, Generator

from app.domain.models import LoginStatus, Platform
from app.infrastructure.automation.page_wrapper import AutomationPage
from app.infrastructure.automation.platforms._helpers import (
    host_and_path, semantic_candidate_visible, semantic_resolution_message, wait_or_cancel,
)
from app.infrastructure.automation.semantic_types import ResolutionFailure, SemanticIntent


def _is_youtube_destination(url: str) -> bool:
    host, _ = host_and_path(url)
    return host == "youtube.com" or host.endswith(".youtube.com")


def _is_google_checkpoint(page: AutomationPage, url: str) -> bool:
    lowered_url = url.lower()
    return bool(
        "signin/v2/challenge" in lowered_url
        or "signin/challenge" in lowered_url
        or "twofactor" in lowered_url
        or page.find("text:Verify it's you", timeout=0.1)
        or page.find("text:Confirm it's you", timeout=0.1)
    )


def _is_google_dead(page: AutomationPage, url: str) -> bool:
    lowered_url = url.lower()
    return bool(
        "disabled" in lowered_url
        or page.find("text:Your account has been disabled", timeout=0.1)
    )


def _has_google_login_error(page: AutomationPage) -> bool:
    return bool(
        page.find("text:Wrong password", timeout=0.1)
        or page.find("text:Couldn't find your Google Account", timeout=0.1)
    )


def _wait_for_google_password_stage(
    page: AutomationPage,
    cancellation_event: threading.Event | None,
) -> str:
    for _ in range(16):
        if _has_google_login_error(page):
            return "account_error"
        if _is_google_dead(page, page.url):
            return "dead"
        if _is_google_checkpoint(page, page.url):
            return "checkpoint"
        if semantic_candidate_visible(page, Platform.YOUTUBE, SemanticIntent.PASSWORD_INPUT):
            return "ready"
        if wait_or_cancel(0.5, cancellation_event):
            return "cancelled"
    return "timeout"


def login_youtube(
    page: AutomationPage,
    username: str,
    password: str,
    log_func: Callable[[str], Dict[str, Any]],
    cancellation_event: threading.Event | None = None,
) -> Generator[Dict[str, Any], None, LoginStatus]:
    yield log_func("Opening Google sign-in for YouTube...")
    page.goto(
        "https://accounts.google.com/ServiceLogin?service=youtube&continue=https://www.youtube.com/"
    )
    if _is_youtube_destination(page.url) and page.find("css:#avatar-btn", timeout=2):
        yield log_func("An existing Google/YouTube session was detected.")
        return LoginStatus.LOGGED_IN

    for _ in range(10):
        if semantic_candidate_visible(
            page, Platform.YOUTUBE, SemanticIntent.EMAIL_OR_PHONE_INPUT,
        ):
            break
        if wait_or_cancel(0.5, cancellation_event):
            yield log_func("Google/YouTube login was cancelled.")
            return LoginStatus.LOGGED_OUT
    identifier_intents = (
        SemanticIntent.EMAIL_OR_PHONE_INPUT,
        SemanticIntent.CONTINUE_CONTROL,
    )
    identifier_results = page.find_semantic_many(
        Platform.YOUTUBE, identifier_intents, cancellation_event,
    )
    email_resolution = identifier_results[SemanticIntent.EMAIL_OR_PHONE_INPUT]
    continue_resolution = identifier_results[SemanticIntent.CONTINUE_CONTROL]
    for label, resolution in (
        ("email input", email_resolution),
        ("continue control", continue_resolution),
    ):
        yield log_func(semantic_resolution_message("Google", label, resolution))
        if resolution.failure == ResolutionFailure.CANCELLED:
            yield log_func("Google/YouTube login was cancelled.")
            return LoginStatus.LOGGED_OUT

    email_input = email_resolution.element
    if not email_input:
        yield log_func("Google email input was not found.")
        return LoginStatus.LOGGED_OUT
    email_input.input(username)
    if wait_or_cancel(1, cancellation_event):
        yield log_func("Google/YouTube login was cancelled.")
        return LoginStatus.LOGGED_OUT
    next_btn = continue_resolution.element
    if next_btn:
        next_btn.click()
    else:
        yield log_func("Google continue control was not resolved; submitting by keyboard.")
        email_input.press("Enter")
    stage = _wait_for_google_password_stage(page, cancellation_event)
    if stage == "cancelled":
        yield log_func("Google/YouTube login was cancelled.")
        return LoginStatus.LOGGED_OUT
    if stage == "account_error":
        yield log_func("The Google account was not found.")
        return LoginStatus.LOGGED_OUT
    if stage == "dead":
        yield log_func("Google reports that the account is disabled.")
        return LoginStatus.DEAD
    if stage == "checkpoint":
        yield log_func("Google requires a security verification.")
        return LoginStatus.CHECKPOINT

    password_intents = (
        SemanticIntent.PASSWORD_INPUT,
        SemanticIntent.LOGIN_SUBMIT_CONTROL,
    )
    password_results = page.find_semantic_many(
        Platform.YOUTUBE, password_intents, cancellation_event,
    )
    pass_resolution = password_results[SemanticIntent.PASSWORD_INPUT]
    submit_resolution = password_results[SemanticIntent.LOGIN_SUBMIT_CONTROL]
    for label, resolution in (
        ("password input", pass_resolution),
        ("submit control", submit_resolution),
    ):
        yield log_func(semantic_resolution_message("Google", label, resolution))
        if resolution.failure == ResolutionFailure.CANCELLED:
            yield log_func("Google/YouTube login was cancelled.")
            return LoginStatus.LOGGED_OUT

    pass_input = pass_resolution.element
    if not pass_input:
        yield log_func(
            "Google password input was not found; a CAPTCHA or challenge may be blocking it."
        )
        return LoginStatus.CHECKPOINT
    pass_input.input(password)
    if wait_or_cancel(1, cancellation_event):
        yield log_func("Google/YouTube login was cancelled.")
        return LoginStatus.LOGGED_OUT
    password_next = submit_resolution.element
    if password_next:
        password_next.click()
    else:
        yield log_func("Google submit control was not resolved; submitting by keyboard.")
        pass_input.press("Enter")

    for _ in range(20):
        if wait_or_cancel(0.5, cancellation_event):
            yield log_func("Google/YouTube login was cancelled.")
            return LoginStatus.LOGGED_OUT
        url = page.url
        if _is_youtube_destination(url):
            yield log_func("Google/YouTube login succeeded.")
            return LoginStatus.LOGGED_IN
        if _is_google_dead(page, url):
            yield log_func("Google reports that the account is disabled.")
            return LoginStatus.DEAD
        if _has_google_login_error(page):
            yield log_func("Google rejected the login credentials.")
            return LoginStatus.LOGGED_OUT
        if _is_google_checkpoint(page, url):
            yield log_func(
                "Google requires a security verification; waiting up to 60 seconds for manual completion."
            )
            for _ in range(120):
                if wait_or_cancel(0.5, cancellation_event):
                    yield log_func("Google/YouTube login was cancelled.")
                    return LoginStatus.LOGGED_OUT
                if _is_youtube_destination(page.url):
                    yield log_func("Google/YouTube login succeeded after verification.")
                    return LoginStatus.LOGGED_IN
                if _is_google_dead(page, page.url):
                    yield log_func("Google reports that the account is disabled.")
                    return LoginStatus.DEAD
            yield log_func("Google verification was not completed before the timeout.")
            return LoginStatus.CHECKPOINT
    yield log_func("Google/YouTube login did not reach a conclusive state before the timeout.")
    return LoginStatus.LOGGED_OUT
