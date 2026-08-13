# File: backend/app/infrastructure/automation/drission_page.py
import os
from typing import Callable
from app.application.interfaces import BrowserContextManager

from app.infrastructure.automation.adapters import DrissionPageWrapper
from app.infrastructure.automation.gemlogin_browser import GemLoginBrowser
from app.infrastructure.automation.base_service import BaseAutomationService
from app.infrastructure.ai.factory import get_ai_composition


def default_browser_manager_factory(profile_key: str, profile_name: str | None = None) -> BrowserContextManager:
    # pyrefly: ignore [missing-import]
    from dotenv import load_dotenv

    _ = load_dotenv()
    gemlogin_api_url = os.getenv("GEMLOGIN_API_URL", "http://127.0.0.1:1010/api")
    gemlogin_profile_id = os.getenv("GEMLOGIN_PROFILE_ID")
    gemlogin_profile_name = profile_name or os.getenv("GEMLOGIN_PROFILE_NAME")
    return GemLoginBrowser(
        profile_key=profile_key,
        gemlogin_api_url=gemlogin_api_url,
        gemlogin_profile_id=gemlogin_profile_id,
        gemlogin_profile_name=gemlogin_profile_name,
    )


class DrissionPageAutomationService(BaseAutomationService):
    def __init__(
        self,
        browser_manager_factory: Callable[[str, str | None], BrowserContextManager] | None = None,
    ):
        _config, runtime, context_factory = get_ai_composition()
        super().__init__(
            browser_manager_factory=browser_manager_factory or default_browser_manager_factory,
            page_wrapper_class=DrissionPageWrapper,
            ai_runtime=runtime, context_factory=context_factory,
        )


