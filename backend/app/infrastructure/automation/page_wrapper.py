# File: backend/app/infrastructure/automation/page_wrapper.py
"""
Driver-agnostic browser page abstraction layer.

This module defines the AutomationPage and AutomationElement abstract interfaces
that decouple platform login scripts from specific browser driver implementations
(DrissionPage, Playwright, etc.).

Canonical Selector Format (used by ALL platform scripts):
  css:selector   -> Standard CSS selector  (e.g. "css:input[name='email']")
  text:value     -> Partial text match      (e.g. "text:Next")
  xpath://expr   -> XPath expression        (e.g. "xpath://button[@type='submit']")
  #id            -> ID shorthand            (e.g. "#email") -- pass-through, CSS-compatible

Concrete adapter implementations are in:
  - adapters/drissionpage_adapter.py  (DrissionPageWrapper, DrissionPageElement)
  - adapters/playwright_adapter.py    (PlaywrightPageWrapper, PlaywrightElement)
"""

from __future__ import annotations

from abc import ABC, abstractmethod


class AutomationElement(ABC):
    """
    Driver-agnostic handle to a single located DOM element.

    Instances are returned by AutomationPage.find() and AutomationPage.find_first().
    They become invalid (stale) once the page navigates or the DOM mutates.
    """

    @abstractmethod
    def input(self, text: str) -> None:
        """
        Clear the element's current value and type the given text.

        Use press("Enter") to submit a form via keyboard instead of this method.

        Raises:
            RuntimeError: if the element is stale or the field is not writable.
        """
    @abstractmethod
    def click(self, by_js: bool = False) -> None:
        """
        Click the element.

        Args:
            by_js: If True, attempt a JavaScript-dispatched click as a fallback
                   for elements blocked by CSS overlays or focus traps.
                   DrissionPage: calls element.click(by_js=True).
                   Playwright: calls page.evaluate("el => el.click()", handle),
                               then falls back to press("Enter") if that also fails.

        Raises:
            RuntimeError: if the click could not be performed through any strategy.
        """

    @abstractmethod
    def press(self, key: str) -> None:
        """
        Send a keyboard key event to the element.

        Key names follow the Playwright convention: "Enter", "Tab", "Escape".
        DrissionPage maps "Enter" -> input newline character, "Tab" -> input tab.

        Raises:
            RuntimeError: if the element is not interactable.
        """

    @abstractmethod
    def exists(self) -> bool:
        """
        Immediately check whether the element is still present in the DOM.

        This is a non-waiting check. Returns False if the element became stale
        after it was located. Never raises.
        """


class AutomationPage(ABC):
    """
    Driver-agnostic browser page control interface.

    All platform login scripts (platforms/facebook.py, etc.) interact exclusively
    with this interface. Concrete adapters translate method calls to the respective
    browser driver API (DrissionPage or Playwright).

    Thread safety: NOT thread-safe. Each automation session owns a single instance.
    """

    @abstractmethod
    def goto(self, url: str) -> None:
        """
        Navigate the browser to the given URL.

        Blocks until the navigation is committed (not necessarily fully loaded).

        Raises:
            RuntimeError: if navigation fails catastrophically (e.g. DNS failure,
                          invalid URL scheme).
        """

    @abstractmethod
    def find(self, selector: str, timeout: float = 5.0) -> AutomationElement | None:
        """
        Search for a single element matching the canonical selector.

        Args:
            selector: A canonical selector string (see module docstring for format).
            timeout:  Maximum seconds to wait for the element to appear.

        Returns:
            An AutomationElement if the element appears within the timeout,
            or None if the timeout expires. NEVER raises on timeout.
        """

    @abstractmethod
    def find_first(self, *selectors: str, timeout: float = 5.0) -> AutomationElement | None:
        """
        Try each selector in order, returning the first matching element.

        The timeout budget is distributed evenly across selectors (minimum 0.5 s
        per probe) to avoid N x timeout slowdown on fallback chains.

        Args:
            *selectors: One or more canonical selector strings tried in order.
            timeout:    Total budget in seconds across all selector probes.

        Returns:
            The first AutomationElement found, or None if no selector matched.
            NEVER raises on timeout.
        """

    @property
    @abstractmethod
    def url(self) -> str:
        """
        Return the current page URL as a plain string.

        Always safe to read; returns an empty string if no page has loaded yet.
        """

    @property
    @abstractmethod
    def html(self) -> str:
        """
        Return the current page's full HTML source as a plain string.

        Always safe to read; returns an empty string if no page has loaded yet.
        DrissionPage: page.html
        Playwright:   page.content()
        """

    @abstractmethod
    def capture_screenshot_base64(self, mask_sensitive: bool = True) -> str:
        """Capture the current viewport as base64 PNG, masking editable fields by default."""

    @abstractmethod
    def find_with_ai_fallback(self, selector: str, hint_text: str, timeout: float = 5.0) -> AutomationElement | None:
        """
        Search for an element using canonical selector first. If not found and AI Fallback
        is enabled, capture page screenshot + DOM snippet and query Vision LLM for element selector.

        Args:
            selector: Initial canonical selector to attempt.
            hint_text: Semantic description of target element (e.g. 'Email input field').
            timeout: Initial search timeout in seconds.

        Returns:
            AutomationElement if found via static selector or AI prediction, else None.
        """
