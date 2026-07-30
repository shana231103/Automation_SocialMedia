# File: backend/app/infrastructure/automation/adapters/drissionpage_adapter.py
"""
DrissionPage concrete adapter implementing AutomationPage and AutomationElement.

Translates canonical selector strings (css:, text:, xpath: prefixes) to the
DrissionPage element-search syntax, then delegates all method calls to the
underlying ChromiumPage and ChromiumElement objects.
"""

from __future__ import annotations

from typing import Any

from DrissionPage import ChromiumPage

from app.infrastructure.automation.page_wrapper import AutomationElement, AutomationPage


# ---------------------------------------------------------------------------
# Selector translation
# ---------------------------------------------------------------------------

_KNOWN_PREFIXES = ("css:", "text:", "xpath:", "tag:", "t:", "x:", "@")


def _to_drission_selector(selector: str) -> str:
    """
    Ensure bare CSS selectors are prefixed with 'css:' so DrissionPage
    uses the correct search strategy.

    Selectors already using a known DrissionPage prefix pass through unchanged.
    Examples:
        "css:input[name='email']" -> "css:input[name='email']"  (pass-through)
        "text:Next"               -> "text:Next"                 (pass-through)
        "xpath://button"          -> "xpath://button"            (pass-through)
        "#email"                  -> "css:#email"
        "[role='feed']"           -> "css:[role='feed']"
    """
    if any(selector.startswith(p) for p in _KNOWN_PREFIXES):
        return selector
    return f"css:{selector}"


# ---------------------------------------------------------------------------
# AutomationElement implementation
# ---------------------------------------------------------------------------

class DrissionPageElement(AutomationElement):
    """Wraps a DrissionPage ChromiumElement as an AutomationElement."""

    _KEY_MAP: dict[str, str] = {
        "Enter": "\n",
        "Tab": "\t",
        "Escape": "\x1b",
    }

    def __init__(self, element: Any) -> None:
        self._el = element

    def input(self, text: str) -> None:
        try:
            self._el.input(text)
        except Exception as exc:
            raise RuntimeError(f"DrissionPage input() failed: {exc}") from exc

    def click(self, by_js: bool = False) -> None:
        try:
            self._el.click(by_js=by_js)
        except Exception as exc:
            raise RuntimeError(f"DrissionPage click(by_js={by_js}) failed: {exc}") from exc

    def press(self, key: str) -> None:
        char = self._KEY_MAP.get(key, key)
        try:
            self._el.input(char)
        except Exception as exc:
            raise RuntimeError(f"DrissionPage press({key!r}) failed: {exc}") from exc

    def exists(self) -> bool:
        try:
            return bool(self._el)
        except Exception:
            return False


# ---------------------------------------------------------------------------
# AutomationPage implementation
# ---------------------------------------------------------------------------

class DrissionPageWrapper(AutomationPage):
    """Wraps a DrissionPage ChromiumPage as an AutomationPage."""

    def __init__(self, page: ChromiumPage) -> None:
        self._page = page

    def goto(self, url: str) -> None:
        try:
            self._page.get(url)
        except Exception as exc:
            raise RuntimeError(f"DrissionPage goto({url!r}) failed: {exc}") from exc

    def find(self, selector: str, timeout: float = 5.0) -> DrissionPageElement | None:
        native_selector = _to_drission_selector(selector)
        try:
            el = self._page.ele(native_selector, timeout=timeout)
            return DrissionPageElement(el) if el else None
        except Exception:
            return None

    def find_first(self, *selectors: str, timeout: float = 5.0) -> DrissionPageElement | None:
        if not selectors:
            return None
        # Distribute budget evenly; enforce minimum 0.5s per probe.
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
            return self._page.html or ""
        except Exception:
            return ""

    def find_with_ai_fallback(self, selector: str, hint_text: str, timeout: float = 5.0) -> DrissionPageElement | None:
        element = self.find(selector, timeout=timeout)
        if element is not None:
            return element

        from app.infrastructure.ai.vision_client import MultimodalVisionClient
        from app.infrastructure.ai.dom_parser import DOMParser
        import base64

        vision_client = MultimodalVisionClient()
        if not vision_client.is_enabled():
            return None

        try:
            # Capture screenshot as bytes
            img_bytes = self._page.get_screenshot(as_bytes=True)
            img_b64 = base64.b64encode(img_bytes).decode("utf-8") if isinstance(img_bytes, bytes) else ""

            # Extract DOM snippet
            dom_snippet = DOMParser.extract_interactable_snippet(self.html)

            # Query Vision LLM for prediction
            prediction = vision_client.predict_element(img_b64, dom_snippet, hint_text)
            if prediction.selector:
                predicted_el = self.find(prediction.selector, timeout=2.0)
                if predicted_el:
                    return predicted_el
        except Exception:
            pass

        return None
