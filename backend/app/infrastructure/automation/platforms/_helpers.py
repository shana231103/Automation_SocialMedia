"""Small shared helpers for responsive, driver-agnostic platform flows."""

from __future__ import annotations

import threading
import time
from urllib.parse import urlparse


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
