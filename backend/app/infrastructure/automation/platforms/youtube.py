"""Driver-agnostic YouTube/Google login automation script."""

from __future__ import annotations

import threading
from typing import Any, Callable, Dict, Generator

from app.domain.models import LoginStatus
from app.infrastructure.automation.page_wrapper import AutomationPage
from app.infrastructure.automation.platforms._helpers import host_and_path, wait_or_cancel


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


def login_youtube(
    page: AutomationPage,
    username: str,
    password: str,
    log_func: Callable[[str], Dict[str, Any]],
    cancellation_event: threading.Event | None = None,
) -> Generator[Dict[str, Any], None, LoginStatus]:
    yield log_func("Opening Google sign-in for YouTube...")
    page.goto("https://accounts.google.com/ServiceLogin?service=youtube&continue=https://www.youtube.com/")
    if _is_youtube_destination(page.url) and page.find("css:#avatar-btn", timeout=2):
        yield log_func("An existing Google/YouTube session was detected.")
        return LoginStatus.LOGGED_IN

    email_input = page.find("css:input[type='email']", timeout=5)
    if not email_input:
        email_input = page.find("#identifierId", timeout=2)
    if not email_input:
        email_input = page.find_with_ai_fallback(
            "css:input[type='email']", "Google email input", timeout=2
        )
    if not email_input:
        yield log_func("Google email input was not found.")
        return LoginStatus.LOGGED_OUT

    email_input.input(username)
    if wait_or_cancel(1, cancellation_event):
        yield log_func("Google/YouTube login was cancelled.")
        return LoginStatus.LOGGED_OUT
    next_btn = page.find_first(
        "css:#identifierNext",
        "xpath://button[.//span[text()='Next']]",
        "xpath://button[.//span[text()='Tiếp theo']]",
        timeout=3,
    )
    if next_btn:
        next_btn.click()
    else:
        email_input.press("Enter")

    pass_input = None
    account_error = False
    for _ in range(16):
        pass_input = page.find("css:input[type='password']", timeout=0.1)
        account_error = bool(
            page.find("text:Couldn't find your Google Account", timeout=0.1)
        )
        if pass_input or account_error:
            break
        if wait_or_cancel(0.5, cancellation_event):
            yield log_func("Google/YouTube login was cancelled.")
            return LoginStatus.LOGGED_OUT
    if account_error:
        yield log_func("The Google account was not found.")
        return LoginStatus.LOGGED_OUT
    if not pass_input:
        pass_input = page.find_with_ai_fallback(
            "css:input[type='password']", "Google password input", timeout=2
        )
    if not pass_input:
        yield log_func("Google password input was not found; a CAPTCHA or challenge may be blocking it.")
        return LoginStatus.CHECKPOINT

    pass_input.input(password)
    if wait_or_cancel(1, cancellation_event):
        yield log_func("Google/YouTube login was cancelled.")
        return LoginStatus.LOGGED_OUT
    password_next = page.find_first(
        "css:#passwordNext",
        "xpath://button[.//span[text()='Next']]",
        "xpath://button[.//span[text()='Tiếp theo']]",
        timeout=3,
    )
    if password_next:
        password_next.click()
    else:
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
            yield log_func("Google requires a security verification; waiting up to 60 seconds for manual completion.")
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
