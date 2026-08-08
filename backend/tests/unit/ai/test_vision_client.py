# File: backend/tests/unit/ai/test_vision_client.py
"""Unit tests for DOM parsing and the local Ollama selector client."""

import unittest
from unittest.mock import MagicMock, patch

import requests

from app.infrastructure.ai.dom_parser import DOMParser, InteractableHTMLParser
from app.infrastructure.ai.vision_client import (
    MultimodalVisionClient, SelectorPredictionFailure,
)


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
        self.assertEqual(prediction.failure_code, SelectorPredictionFailure.DISABLED)
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
        self.assertEqual(prediction.failure_code, SelectorPredictionFailure.NONE)
        call = session.post.call_args
        self.assertEqual(call.kwargs["json"]["model"], "qwen3.5:9b")
        self.assertFalse(call.kwargs["json"]["think"])
        self.assertEqual(call.kwargs["json"]["options"]["num_predict"], 256)
        self.assertEqual(call.kwargs["json"]["messages"][0]["images"], ["image-data"])
        self.assertNotIn(
            "failure_code", call.kwargs["json"]["format"]["properties"],
        )
        self.assertFalse(call.kwargs["allow_redirects"])

    def test_timeout_and_invalid_response_fail_safely(self):
        timeout_session = MagicMock()
        timeout_session.post.side_effect = requests.Timeout()
        client = MultimodalVisionClient(enabled=True, http_session=timeout_session)
        timed_out = client.predict_element("image", "<input>", "Email")
        self.assertEqual(timed_out.failure_code, SelectorPredictionFailure.TIMEOUT)
        timeout_session.post.side_effect = requests.ConnectionError()
        unavailable = client.predict_element("image", "<input>", "Email")
        self.assertEqual(unavailable.failure_code, SelectorPredictionFailure.UNAVAILABLE)

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
        self.assertEqual(prediction.failure_code, SelectorPredictionFailure.INVALID_RESPONSE)
        self.assertIn("Invalid", prediction.reasoning)
        response.json.side_effect = ValueError("invalid JSON")
        prediction = client.predict_element("image", "<input>", "Email")
        self.assertEqual(prediction.failure_code, SelectorPredictionFailure.INVALID_RESPONSE)

    def test_http_redirect_and_size_failures_are_typed(self):
        cases = (
            (302, True, b"", SelectorPredictionFailure.REDIRECT_REFUSED),
            (404, False, b"", SelectorPredictionFailure.HTTP_CLIENT_ERROR),
            (503, False, b"", SelectorPredictionFailure.HTTP_SERVER_ERROR),
            (200, False, b"oversized", SelectorPredictionFailure.RESPONSE_TOO_LARGE),
        )
        for status, redirect, content, expected in cases:
            with self.subTest(expected=expected):
                response = MagicMock(
                    status_code=status, is_redirect=redirect, content=content,
                )
                session = MagicMock()
                session.post.return_value = response
                client = MultimodalVisionClient(
                    enabled=True, http_session=session,
                    max_response_bytes=1024,
                )
                if expected == SelectorPredictionFailure.RESPONSE_TOO_LARGE:
                    response.content = b"x" * 1025
                result = client.predict_element("image", "<input>", "Email")
                self.assertEqual(result.failure_code, expected)

    def test_incomplete_evidence_is_non_transport_failure(self):
        client = MultimodalVisionClient(enabled=True, http_session=MagicMock())
        result = client.predict_element("", "<input>", "Email")
        self.assertEqual(
            result.failure_code, SelectorPredictionFailure.INCOMPLETE_EVIDENCE,
        )


if __name__ == "__main__":
    unittest.main()
