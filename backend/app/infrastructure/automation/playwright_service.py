# File: backend/app/infrastructure/automation/playwright_service.py
import os
from typing import Callable
from app.application.interfaces import BrowserContextManager

from app.infrastructure.automation.adapters import PlaywrightPageWrapper
from app.infrastructure.automation.playwright_browser import GemLoginPlaywrightBrowser
from app.infrastructure.automation.base_service import BaseAutomationService


def default_browser_manager_factory(profile_key: str) -> BrowserContextManager:
    from dotenv import load_dotenv
    _ = load_dotenv()
    
    gemlogin_api_url = os.getenv("GEMLOGIN_API_URL", "http://127.0.0.1:1010/api")
    gemlogin_profile_id = os.getenv("GEMLOGIN_PROFILE_ID")
    gemlogin_profile_name = os.getenv("GEMLOGIN_PROFILE_NAME")
    return GemLoginPlaywrightBrowser(
        profile_key=profile_key,
        gemlogin_api_url=gemlogin_api_url,
        gemlogin_profile_id=gemlogin_profile_id,
        gemlogin_profile_name=gemlogin_profile_name,
    )


class PlaywrightAutomationService(BaseAutomationService):
    def __init__(
        self,
        browser_manager_factory: Callable[[str], BrowserContextManager] | None = None,
    ):
        super().__init__(
            browser_manager_factory=browser_manager_factory or default_browser_manager_factory,
            page_wrapper_class=PlaywrightPageWrapper,
        )


