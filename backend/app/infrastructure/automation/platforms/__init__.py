# File: backend/app/infrastructure/automation/platforms/__init__.py
"""
Driver-agnostic platform login automation scripts.

All scripts depend only on the AutomationPage interface.
"""

from app.infrastructure.automation.platforms.facebook import login_facebook
from app.infrastructure.automation.platforms.youtube import login_youtube
from app.infrastructure.automation.platforms.tiktok import login_tiktok
from app.infrastructure.automation.platforms.twitter import login_twitter

__all__ = [
    "login_facebook",
    "login_youtube",
    "login_tiktok",
    "login_twitter",
]
