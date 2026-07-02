# File: backend/app/infrastructure/automation/adapters/__init__.py
"""
Browser driver adapters for the AutomationPage abstraction layer.

Available adapters:
  - DrissionPageWrapper / DrissionPageElement  (DrissionPage driver)
  - PlaywrightPageWrapper / PlaywrightElement  (Playwright sync_api driver)
"""

from app.infrastructure.automation.adapters.drissionpage_adapter import (
    DrissionPageWrapper,
    DrissionPageElement,
)
from app.infrastructure.automation.adapters.playwright_adapter import (
    PlaywrightPageWrapper,
    PlaywrightElement,
)

__all__ = [
    "DrissionPageWrapper",
    "DrissionPageElement",
    "PlaywrightPageWrapper",
    "PlaywrightElement",
]
