# File: backend/app/infrastructure/automation/adapters/playwright_adapter.py
"""Playwright adapter implementing the shared page and element contracts."""

from __future__ import annotations

import base64
import threading
from playwright.sync_api import Locator, Page
from playwright.sync_api import TimeoutError as PlaywrightTimeoutError

from app.domain.models import Platform
from app.infrastructure.automation.page_wrapper import AutomationElement, AutomationPage
from app.infrastructure.automation.semantic_locator import SemanticLocatorResolver
from app.infrastructure.automation.semantic_types import SemanticIntent, SemanticResolution
from app.infrastructure.automation.adapters.sensitive_mask import (
    MASK_SENSITIVE_SCRIPT,
    REMOVE_SENSITIVE_MASK_SCRIPT,
)
def _to_playwright_selector(selector: str) -> str:
    """Translate canonical css/text/xpath prefixes for Playwright."""
    if selector.startswith("css:"):
        return selector[4:]
    if selector.startswith("text:"):
        return f"text={selector[5:]}"
    if selector.startswith("xpath:"):
        return selector[6:]
    return selector


class PlaywrightElement(AutomationElement):
    """Wraps a Playwright Locator (first match) as an AutomationElement."""

    def __init__(self, locator: Locator, page: Page) -> None:
        self._locator = locator
        self._page = page

    def input(self, text: str) -> None:
        try:
            self._locator.fill(text)
        except Exception as exc:
            raise RuntimeError(f"Playwright fill() failed: {exc}") from exc

    def click(self, by_js: bool = False) -> None:
        if not by_js:
            try:
                self._locator.click()
                return
            except Exception as exc:
                raise RuntimeError(f"Playwright click() failed: {exc}") from exc

        # by_js=True: try JS evaluate first, then Enter-key as final fallback.
        try:
            element_handle = self._locator.element_handle(timeout=2000)
            if element_handle:
                self._page.evaluate("el => el.click()", element_handle)
                return
        except Exception:
            element_handle = None

        try:
            self._locator.press("Enter")
        except Exception as exc:
            raise RuntimeError(
                f"Playwright click(by_js=True) failed via JS evaluate and Enter fallback: {exc}"
            ) from exc

    def press(self, key: str) -> None:
        try:
            self._locator.press(key)
        except Exception as exc:
            raise RuntimeError(f"Playwright press({key!r}) failed: {exc}") from exc

    def exists(self) -> bool:
        try:
            return self._locator.count() > 0
        except Exception:
            return False


class PlaywrightPageWrapper(AutomationPage):
    """Wraps a Playwright sync Page as an AutomationPage."""

    def __init__(
        self, page: Page, semantic_resolver: SemanticLocatorResolver | None = None,
    ) -> None:
        self._page = page
        self._semantic_resolver = semantic_resolver or SemanticLocatorResolver()

    def goto(self, url: str) -> None:
        try:
            self._page.goto(url)
        except Exception as exc:
            raise RuntimeError(f"Playwright goto({url!r}) failed: {exc}") from exc

    def find(self, selector: str, timeout: float = 5.0) -> PlaywrightElement | None:
        pw_selector = _to_playwright_selector(selector)
        locator = self._page.locator(pw_selector).first
        try:
            locator.wait_for(state="attached", timeout=timeout * 1000)
            return PlaywrightElement(locator, self._page)
        except PlaywrightTimeoutError:
            return None
        except Exception:
            return None

    def find_first(self, *selectors: str, timeout: float = 5.0) -> PlaywrightElement | None:
        if not selectors:
            return None
        per_probe = max(0.5, timeout / len(selectors))
        for selector in selectors:
            el = self.find(selector, timeout=per_probe)
            if el is not None:
                return el
        return None

    @property
    def url(self) -> str:
        try:
            return self._page.url or ""
        except Exception:
            return ""

    @property
    def html(self) -> str:
        try:
            return self._page.content() or ""
        except Exception:
            return ""

    def capture_screenshot_base64(self, mask_sensitive: bool = True) -> str:
        masked = False
        try:
            if mask_sensitive:
                self._page.evaluate(MASK_SENSITIVE_SCRIPT)
                masked = True
            image_bytes = self._page.screenshot(full_page=False)
            if not isinstance(image_bytes, bytes) or not image_bytes:
                raise RuntimeError("Playwright returned no screenshot bytes")
            return base64.b64encode(image_bytes).decode("ascii")
        except Exception as exc:
            raise RuntimeError(f"Playwright screenshot capture failed: {exc}") from exc
        finally:
            if masked:
                try:
                    self._page.evaluate(REMOVE_SENSITIVE_MASK_SCRIPT)
                except Exception as cleanup_error:
                    del cleanup_error

    def find_semantic(
        self, platform: Platform, intent: SemanticIntent,
        cancellation_event: threading.Event | None = None,
    ) -> SemanticResolution[AutomationElement]:
        return self._semantic_resolver.resolve(
            self, platform, intent, cancellation_event,
        )

    def find_semantic_many(
        self, platform: Platform, intents: tuple[SemanticIntent, ...],
        cancellation_event: threading.Event | None = None,
    ) -> dict[SemanticIntent, SemanticResolution[AutomationElement]]:
        return self._semantic_resolver.resolve_many(
            self, platform, intents, cancellation_event,
        )

    def find_with_ai_fallback(
        self, selector: str, hint_text: str, timeout: float = 5.0,
    ) -> AutomationElement | None:
        return self._semantic_resolver.resolve_legacy(
            self, selector, hint_text, timeout,
        )
