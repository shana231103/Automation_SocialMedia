# File: backend/app/infrastructure/automation/protected_observation.py
"""Capture bounded, privacy-protected browser observations."""

import base64
import hashlib
import json

from app.application.ai_login import ProtectedObservation
from app.domain.models import LoginStatus, Platform
from app.infrastructure.ai.dom_parser import DOMParser
from app.infrastructure.automation.login_status_policy import sanitize_url
from app.infrastructure.automation.page_wrapper import AutomationPage


def capture_protected_observation(page: AutomationPage, platform: Platform,
                                  preliminary_status: LoginStatus | None,
                                  secrets: tuple[str, ...], max_dom_chars: int,
                                  max_screenshot_bytes: int) -> ProtectedObservation:
    screenshot = page.capture_screenshot_base64(mask_sensitive=True)
    image = base64.b64decode(screenshot, validate=True)
    if not image or len(image) > max_screenshot_bytes:
        raise ValueError("Protected screenshot is empty or too large")
    dom = DOMParser.extract_status_snippet(page.html, max_dom_chars, secrets)
    url = sanitize_url(page.url)
    canonical = json.dumps({"platform": platform.value, "url": url, "dom": dom,
                            "image": hashlib.sha256(image).hexdigest()},
                           sort_keys=True).encode("utf-8")
    observation_id = hashlib.sha256(canonical).hexdigest()
    return ProtectedObservation(observation_id, platform, url, screenshot, dom,
                                preliminary_status)
