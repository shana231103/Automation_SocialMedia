# File: backend/app/infrastructure/ai/dom_parser.py
"""HTML DOM Parser utility to extract lightweight interactable elements for AI analysis."""

from html.parser import HTMLParser
from typing import List, Dict


class InteractableHTMLParser(HTMLParser):
    """HTML Parser that extracts interactable elements and key attributes."""
    
    INTERACTABLE_TAGS = {"input", "button", "form", "select", "textarea", "a"}
    KEEP_ATTRS = {"id", "name", "type", "placeholder", "aria-label", "role", "class", "value"}

    def __init__(self):
        super().__init__()
        self.elements: List[str] = []

    def handle_starttag(self, tag: str, attrs: List[tuple]):
        if tag in self.INTERACTABLE_TAGS:
            attr_dict: Dict[str, str] = {k.lower(): v for k, v in attrs if k.lower() in self.KEEP_ATTRS}
            attr_str = " ".join([f'{k}="{v}"' for k, v in attr_dict.items() if v])
            if attr_str:
                self.elements.append(f"<{tag} {attr_str}>")
            else:
                self.elements.append(f"<{tag}>")


class DOMParser:
    """Utility class to parse HTML and generate compact DOM snippets for LLM context."""

    @staticmethod
    def extract_interactable_snippet(html_content: str, max_chars: int = 4000) -> str:
        """
        Extract interactable HTML elements (inputs, buttons, forms) from raw HTML content.

        Args:
            html_content: Raw HTML string of the webpage.
            max_chars: Maximum character budget for the resulting snippet.

        Returns:
            Truncated string containing lightweight HTML representation.
        """
        if not html_content:
            return ""

        parser = InteractableHTMLParser()
        try:
            parser.feed(html_content)
        except Exception:
            # Return raw truncated HTML as fallback if parsing fails
            return html_content[:max_chars]

        snippet = "\n".join(parser.elements)
        if len(snippet) > max_chars:
            return snippet[:max_chars] + "\n...[truncated]"
        return snippet
