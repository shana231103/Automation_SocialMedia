"""Driver-agnostic Facebook login automation script."""

from __future__ import annotations

import threading
from typing import Any, Callable, Dict, Generator

from app.domain.models import LoginStatus
from app.infrastructure.automation.page_wrapper import AutomationPage
from app.infrastructure.automation.platforms._helpers import host_and_path, wait_or_cancel


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
    email_input = page.find_first(
        "css:input[name='email']", "#email", "css:input[type='email']", timeout=1.5,
    )
    pass_input = page.find_first(
        "css:input[name='pass']", "#pass", "css:input[type='password']", timeout=1.5,
    )
    if not email_input:
        yield log_func("Facebook email input changed; asking local AI for a selector...")
        email_input = page.find_with_ai_fallback(
            "css:input[name='email']", "Facebook email or phone input", timeout=0.1,
        )
    if not pass_input:
        yield log_func("Facebook password input changed; asking local AI for a selector...")
        pass_input = page.find_with_ai_fallback(
            "css:input[name='pass']", "Facebook password input", timeout=0.1,
        )
    if not email_input or not pass_input:
        yield log_func("Facebook credential inputs were not found.")
        return LoginStatus.LOGGED_OUT

    email_input.input(username)
    if _cancelled(cancellation_event, 0.5):
        yield log_func("Facebook login was cancelled.")
        return LoginStatus.LOGGED_OUT
    pass_input.input(password)
    if _cancelled(cancellation_event, 0.5):
        yield log_func("Facebook login was cancelled.")
        return LoginStatus.LOGGED_OUT

    login_btn = page.find_first(
        "css:button[name='login']",
        "css:[data-testid='royal_login_button']",
        "css:button[type='submit']",
        "css:input[type='submit']",
        timeout=3,
    )
    try:
        if login_btn:
            login_btn.click()
        else:
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
