"""Driver-agnostic TikTok login automation script."""

from __future__ import annotations

import threading
from typing import Any, Callable, Dict, Generator

from app.domain.models import LoginStatus
from app.infrastructure.automation.page_wrapper import AutomationPage
from app.infrastructure.automation.platforms._helpers import wait_or_cancel


def _is_tiktok_authenticated(page: AutomationPage) -> bool:
    return bool(
        page.find("css:[data-e2e='profile-icon']", timeout=0.1)
        or page.find("css:[data-e2e='profile-avatar']", timeout=0.1)
    )


def _requires_tiktok_checkpoint(page: AutomationPage, url: str) -> bool:
    lowered_url = url.lower()
    return bool(
        "captcha" in lowered_url
        or "challenge" in lowered_url
        or page.find("css:[id='captcha-wrapper']", timeout=0.1)
        or page.find("css:.captcha-slider", timeout=0.1)
        or page.find("css:.captcha_verify_container", timeout=0.1)
    )


def _is_tiktok_dead(page: AutomationPage, url: str) -> bool:
    lowered_url = url.lower()
    return bool(
        "account-suspended" in lowered_url
        or "account-disabled" in lowered_url
        or page.find("text:Your account has been suspended", timeout=0.1)
        or page.find("text:Your account has been permanently banned", timeout=0.1)
    )


def login_tiktok(
    page: AutomationPage,
    username: str,
    password: str,
    log_func: Callable[[str], Dict[str, Any]],
    cancellation_event: threading.Event | None = None,
) -> Generator[Dict[str, Any], None, LoginStatus]:
    yield log_func("Opening TikTok login...")
    page.goto("https://www.tiktok.com/login/phone-or-email/email")
    if _is_tiktok_authenticated(page):
        yield log_func("An existing TikTok session was detected.")
        return LoginStatus.LOGGED_IN

    user_input = page.find("css:input[name='username']", timeout=5)
    pass_input = page.find("css:input[type='password']", timeout=5)
    if not user_input:
        user_input = page.find_with_ai_fallback(
            "css:input[name='username']", "TikTok email or username input", timeout=2
        )
    if not pass_input:
        pass_input = page.find_with_ai_fallback(
            "css:input[type='password']", "TikTok password input", timeout=2
        )
    if not user_input or not pass_input:
        yield log_func("TikTok credential inputs were not found.")
        return LoginStatus.LOGGED_OUT

    user_input.input(username)
    if wait_or_cancel(0.5, cancellation_event):
        yield log_func("TikTok login was cancelled.")
        return LoginStatus.LOGGED_OUT
    pass_input.input(password)
    if wait_or_cancel(0.5, cancellation_event):
        yield log_func("TikTok login was cancelled.")
        return LoginStatus.LOGGED_OUT

    submit_btn = page.find("css:button[type='submit']", timeout=2)
    if submit_btn:
        submit_btn.click()
    else:
        pass_input.press("Enter")
    yield log_func("Waiting for TikTok to respond; solve any CAPTCHA manually if shown.")

    for _ in range(16):
        if wait_or_cancel(0.5, cancellation_event):
            yield log_func("TikTok login was cancelled.")
            return LoginStatus.LOGGED_OUT
        if _requires_tiktok_checkpoint(page, page.url):
            yield log_func("TikTok requires CAPTCHA or a security verification.")
            if wait_or_cancel(15, cancellation_event):
                yield log_func("TikTok login was cancelled.")
                return LoginStatus.LOGGED_OUT
            break
        if _is_tiktok_authenticated(page):
            yield log_func("TikTok login succeeded.")
            return LoginStatus.LOGGED_IN

    for _ in range(10):
        if wait_or_cancel(0.5, cancellation_event):
            yield log_func("TikTok login was cancelled.")
            return LoginStatus.LOGGED_OUT
        url = page.url
        if _is_tiktok_authenticated(page):
            yield log_func("TikTok login succeeded.")
            return LoginStatus.LOGGED_IN
        if _is_tiktok_dead(page, url):
            yield log_func("TikTok reports that the account is suspended or banned.")
            return LoginStatus.DEAD
        if _requires_tiktok_checkpoint(page, url):
            yield log_func("TikTok CAPTCHA or verification is still pending.")
            return LoginStatus.CHECKPOINT

    yield log_func("TikTok login did not reach a conclusive state before the timeout.")
    return LoginStatus.LOGGED_OUT
