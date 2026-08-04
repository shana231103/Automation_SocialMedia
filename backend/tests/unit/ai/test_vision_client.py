# File: backend/tests/unit/ai/test_vision_client.py
"""Unit tests for DOM parsing and the local Ollama selector client."""

import unittest
from unittest.mock import MagicMock, patch

import requests

from app.infrastructure.ai.dom_parser import DOMParser, InteractableHTMLParser
from app.infrastructure.ai.vision_client import MultimodalVisionClient


class TestDOMParser(unittest.TestCase):
    """Test suite for DOMParser snippet extraction."""

    def test_extract_interactable_snippet(self):
        sample_html = """
        <html><body><div>Unrelated text</div><form id="loginForm">
        <input name="email" id="email_id" placeholder="Enter email" />
        <input name="pass" type="password" /><button type="submit">Login</button>
        </form></body></html>
        """
        snippet = DOMParser.extract_interactable_snippet(sample_html)
        self.assertIn('<form id="loginForm">', snippet)
        self.assertIn('name="email"', snippet)
        self.assertIn('type="password"', snippet)
        self.assertNotIn("Unrelated text", snippet)

    def test_empty_html_returns_empty_string(self):
        self.assertEqual(DOMParser.extract_interactable_snippet(""), "")

    def test_status_snippet_removes_values_and_explicit_secrets(self):
        html = '<input name="email" value="user@example.com"><div aria-label="user@example.com">'
        snippet = DOMParser.extract_status_snippet(html, secrets=("user@example.com",))
        self.assertNotIn("value=", snippet)
        self.assertNotIn("user@example.com", snippet)
        self.assertIn("[redacted]", snippet)

    def test_parser_failure_never_returns_raw_html(self):
        with patch.object(InteractableHTMLParser, "feed", side_effect=ValueError("broken")):
            self.assertEqual(DOMParser.extract_status_snippet('<input value="secret">'), "")


class TestMultimodalVisionClient(unittest.TestCase):
    """Test suite for loopback Ollama selector interactions."""

    def test_disabled_flag_skips_http(self):
        session = MagicMock()
        client = MultimodalVisionClient(enabled=False, http_session=session)
        prediction = client.predict_element("image", "<input>", "Username input")
        self.assertFalse(client.is_enabled())
        self.assertIsNone(prediction.selector)
        session.post.assert_not_called()

    def test_defaults_to_enabled_local_qwen_model(self):
        with patch.dict("os.environ", {}, clear=True):
            client = MultimodalVisionClient(http_session=MagicMock())
        self.assertTrue(client.is_enabled())
        self.assertEqual(client.provider, "ollama")
        self.assertEqual(client.model, "qwen3.5:9b")

    def test_rejects_non_loopback_ollama_url(self):
        with self.assertRaises(ValueError):
            MultimodalVisionClient(base_url="https://ollama.example.com")

    def test_valid_structured_response_and_payload(self):
        response = MagicMock()
        response.is_redirect = False
        response.status_code = 200
        response.content = b"valid"
        response.json.return_value = {
            "message": {
                "content": '{"selector":"css: #email_id","confidence":0.95,'
                '"reasoning":"Matched email field"}',
            },
        }
        session = MagicMock()
        session.post.return_value = response
        client = MultimodalVisionClient(enabled=True, http_session=session)

        prediction = client.predict_element("image-data", '<input id="email_id">', "Email input")

        self.assertEqual(prediction.selector, "css:#email_id")
        self.assertEqual(prediction.confidence, 0.95)
        call = session.post.call_args
        self.assertEqual(call.kwargs["json"]["model"], "qwen3.5:9b")
        self.assertFalse(call.kwargs["json"]["think"])
        self.assertEqual(call.kwargs["json"]["options"]["num_predict"], 256)
        self.assertEqual(call.kwargs["json"]["messages"][0]["images"], ["image-data"])
        self.assertFalse(call.kwargs["allow_redirects"])

    def test_timeout_and_invalid_response_fail_safely(self):
        timeout_session = MagicMock()
        timeout_session.post.side_effect = requests.Timeout()
        client = MultimodalVisionClient(enabled=True, http_session=timeout_session)
        self.assertIsNone(client.predict_element("image", "<input>", "Email").selector)

        response = MagicMock()
        response.is_redirect = False
        response.status_code = 200
        response.content = b"invalid"
        response.json.return_value = {"message": {"content": "not-json"}}
        invalid_session = MagicMock()
        invalid_session.post.return_value = response
        client = MultimodalVisionClient(enabled=True, http_session=invalid_session)
        prediction = client.predict_element("image", "<input>", "Email")
        self.assertIsNone(prediction.selector)
        self.assertIn("Invalid", prediction.reasoning)


if __name__ == "__main__":
    unittest.main()
