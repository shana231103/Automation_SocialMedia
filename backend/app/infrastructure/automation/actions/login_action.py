# File: backend/app/infrastructure/automation/actions/login_action.py
"""Concrete implementation of the LoginAction automation command."""

from typing import Any, Callable
from app.domain.models import Platform, LoginStatus
from app.infrastructure.automation.page_wrapper import AutomationPage
from app.infrastructure.automation.actions.action_base import AutomationAction

# Import unified, driver-agnostic login scripts
from app.infrastructure.automation.platforms.facebook import login_facebook
from app.infrastructure.automation.platforms.youtube import login_youtube
from app.infrastructure.automation.platforms.tiktok import login_tiktok
from app.infrastructure.automation.platforms.twitter import login_twitter


class LoginAction(AutomationAction):
    """
    Action encapsulating the login flow for various social media platforms.
    """

    def execute(
        self,
        page: AutomationPage,
        params: dict[str, Any],
        log_func: Callable[[str], dict[str, Any]]
    ) -> LoginStatus:
        username = params.get("username")
        password = params.get("password")
        platform = params.get("platform")
        cancellation_event = params.get("cancellation_event")

        if not username or not password or not platform:
            yield log_func("Thiếu thông tin đăng nhập (username, password hoặc platform).")
            return LoginStatus.LOGGED_OUT

        # Resolve correct platform login script
        if platform == Platform.FACEBOOK:
            status = yield from login_facebook(page, username, password, log_func, cancellation_event)
        elif platform == Platform.YOUTUBE:
            status = yield from login_youtube(page, username, password, log_func, cancellation_event)
        elif platform == Platform.TIKTOK:
            status = yield from login_tiktok(page, username, password, log_func, cancellation_event)
        elif platform == Platform.TWITTER:
            status = yield from login_twitter(page, username, password, log_func, cancellation_event)
        else:
            yield log_func(f"Nền tảng {platform} chưa được hỗ trợ.")
            status = LoginStatus.LOGGED_OUT

        return status
