"""Driver-agnostic X (Twitter) login automation script."""

from __future__ import annotations

import threading
from typing import Any, Callable, Dict, Generator

from app.domain.models import LoginStatus
from app.infrastructure.automation.page_wrapper import AutomationPage
from app.infrastructure.automation.platforms._helpers import host_and_path, wait_or_cancel


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

    username_input = None
    for _ in range(16):
        username_input = page.find_first(
            "css:input[name='text']",
            "css:input[autocomplete='username']",
            "css:input[type='text']",
            timeout=0.1,
        )
        if username_input:
            break
        if wait_or_cancel(0.5, cancellation_event):
            yield log_func("X login was cancelled.")
            return LoginStatus.LOGGED_OUT
    if not username_input:
        username_input = page.find_with_ai_fallback(
            "css:input[name='text']", "X (Twitter) username or email input", timeout=2
        )
    if not username_input:
        yield log_func("X username input was not found.")
        return LoginStatus.LOGGED_OUT

    username_input.input(username)
    if wait_or_cancel(0.5, cancellation_event):
        yield log_func("X login was cancelled.")
        return LoginStatus.LOGGED_OUT
    next_btn = page.find_first(
        "css:button[data-testid='ocfEnterTextNextButton']",
        "xpath://button[.//span[text()='Next']]",
        "xpath://button[.//span[text()='Tiếp theo']]",
        timeout=3,
    )
    if next_btn:
        next_btn.click()
    else:
        username_input.press("Enter")

    pass_input = None
    confirmation_input = None
    for _ in range(16):
        pass_input = page.find("css:input[name='password']", timeout=0.1)
        confirmation_input = page.find("css:input[data-testid='ocfEnterTextTextInput']", timeout=0.1)
        if pass_input or confirmation_input:
            break
        if wait_or_cancel(0.5, cancellation_event):
            yield log_func("X login was cancelled.")
            return LoginStatus.LOGGED_OUT
    if not pass_input and not confirmation_input:
        pass_input = page.find_with_ai_fallback(
            "css:input[name='password']", "X (Twitter) password input", timeout=2
        )
    if confirmation_input:
        yield log_func("X requires an email or phone verification step.")
        return LoginStatus.CHECKPOINT
    if not pass_input:
        yield log_func("X password input was not found.")
        return LoginStatus.LOGGED_OUT

    pass_input.input(password)
    if wait_or_cancel(0.5, cancellation_event):
        yield log_func("X login was cancelled.")
        return LoginStatus.LOGGED_OUT
    login_btn = page.find_first(
        "css:button[data-testid='LoginForm_Login_Button']",
        "xpath://button[.//span[text()='Log in']]",
        "xpath://button[.//span[text()='Đăng nhập']]",
        timeout=3,
    )
    if login_btn:
        login_btn.click()
    else:
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
