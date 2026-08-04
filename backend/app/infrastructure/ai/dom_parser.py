# File: backend/app/infrastructure/ai/dom_parser.py
"""Extract compact, privacy-safe DOM evidence for local AI analysis."""

from html import escape
from html.parser import HTMLParser


class InteractableHTMLParser(HTMLParser):
    """Collect selected tags without form values or executable content."""

    INTERACTABLE_TAGS = {"input", "button", "form", "select", "textarea", "a"}
    STATUS_TAGS = INTERACTABLE_TAGS | {"div", "img", "main", "nav", "aside"}
    KEEP_ATTRS = {
        "id", "name", "type", "placeholder", "aria-label", "role", "class",
        "href", "data-testid", "data-e2e",
    }

    def __init__(self, status_mode: bool = False):
        super().__init__()
        self.elements: list[str] = []
        self.allowed_tags = self.STATUS_TAGS if status_mode else self.INTERACTABLE_TAGS

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag not in self.allowed_tags:
            return
        kept = {key.lower(): escape(value, quote=True) for key, value in attrs
                if value and key.lower() in self.KEEP_ATTRS}
        attr_text = " ".join(f'{key}="{value}"' for key, value in kept.items())
        self.elements.append(f"<{tag}{' ' + attr_text if attr_text else ''}>")


class DOMParser:
    """Utility class to parse HTML and generate compact DOM snippets for LLM context."""

    @staticmethod
    def extract_interactable_snippet(html_content: str, max_chars: int = 4000) -> str:
        """Return interactable tags while excluding user-entered values."""
        return DOMParser._extract(html_content, max_chars, status_mode=False, secrets=())

    @staticmethod
    def extract_status_snippet(
        html_content: str,
        max_chars: int = 6000,
        secrets: tuple[str, ...] = (),
    ) -> str:
        """Return status-relevant DOM with explicit secrets redacted."""
        return DOMParser._extract(html_content, max_chars, status_mode=True, secrets=secrets)

    @staticmethod
    def _extract(
        html_content: str,
        max_chars: int,
        status_mode: bool,
        secrets: tuple[str, ...],
    ) -> str:
        if not html_content:
            return ""
        if max_chars < 1:
            raise ValueError("max_chars must be positive")
        parser = InteractableHTMLParser(status_mode=status_mode)
        try:
            parser.feed(html_content)
        except Exception:
            return ""
        snippet = "\n".join(parser.elements)
        for secret in sorted((value for value in secrets if value), key=len, reverse=True):
            snippet = snippet.replace(secret, "[redacted]")
        if len(snippet) > max_chars:
            return snippet[:max_chars] + "\n...[truncated]"
        return snippet
