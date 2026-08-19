"""Small shared helpers for responsive, driver-agnostic platform flows."""

from __future__ import annotations

import threading
import time
from typing import Any
from urllib.parse import urlparse

from app.domain.models import Platform
from app.infrastructure.automation.locators import get_locator_spec
from app.infrastructure.automation.page_wrapper import AutomationPage
from app.infrastructure.automation.semantic_types import (
    ResolutionSource, SemanticIntent, SemanticResolution,
)


def wait_or_cancel(seconds: float, cancellation_event: threading.Event | None) -> bool:
    """Wait up to ``seconds`` and return True when cancellation was requested."""
    if cancellation_event is None:
        time.sleep(seconds)
        return False
    return cancellation_event.wait(seconds)


def host_and_path(url: str) -> tuple[str, str]:
    """Return normalized hostname/path without treating query-string text as a URL path."""
    parsed = urlparse(url)
    return (parsed.hostname or "").lower(), parsed.path or "/"


def semantic_candidate_visible(
    page: AutomationPage,
    platform: Platform,
    intent: SemanticIntent,
    timeout: float = 0.1,
) -> bool:
    """Check registry candidates locally to avoid capturing a transient page."""
    spec = get_locator_spec(platform, intent)
    if spec is None:
        return False
    try:
        return page.find_first(*spec.selectors, timeout=timeout) is not None
    except Exception:
        return False


def semantic_resolution_message(
    platform_label: str,
    control_label: str,
    resolution: SemanticResolution[Any],
) -> str:
    """Describe resolution source without exposing selectors or evidence."""
    if resolution.source == ResolutionSource.AI:
        return (
            f"{platform_label} {control_label} resolved by the configured AI provider "
            f"in {resolution.ai_attempts} attempt(s)."
        )
    if resolution.source == ResolutionSource.REGISTRY:
        suffix = " after AI attempts" if resolution.ai_attempts else ""
        return f"{platform_label} {control_label} resolved by deterministic fallback{suffix}."
    return (
        f"{platform_label} {control_label} was not resolved after "
        f"{resolution.ai_attempts} AI attempt(s)."
    )
