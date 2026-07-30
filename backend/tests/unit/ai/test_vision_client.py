# File: backend/tests/unit/ai/test_vision_client.py
"""Unit tests for DOMParser and MultimodalVisionClient."""

import unittest
from unittest.mock import patch, MagicMock
from app.infrastructure.ai.dom_parser import DOMParser
from app.infrastructure.ai.vision_client import MultimodalVisionClient, ElementPrediction


class TestDOMParser(unittest.TestCase):
    """Test suite for DOMParser snippet extraction."""

    def test_extract_interactable_snippet(self):
        sample_html = """
        <html>
            <body>
                <div>Unrelated text</div>
                <form id="loginForm">
                    <input name="email" id="email_id" placeholder="Enter email" />
                    <input name="pass" type="password" />
                    <button type="submit">Login</button>
                </form>
            </body>
        </html>
        """
        snippet = DOMParser.extract_interactable_snippet(sample_html)
        self.assertIn('<form id="loginForm">', snippet)
        self.assertIn('name="email"', snippet)
        self.assertIn('type="password"', snippet)
        self.assertNotIn("Unrelated text", snippet)

    def test_empty_html_returns_empty_string(self):
        self.assertEqual(DOMParser.extract_interactable_snippet(""), "")


class TestMultimodalVisionClient(unittest.TestCase):
    """Test suite for MultimodalVisionClient API interactions."""

    def test_disabled_when_flag_not_set(self):
        with patch.dict("os.environ", {"ENABLE_AI_FALLBACK": "false"}, clear=True):
            client = MultimodalVisionClient()
            self.assertFalse(client.is_enabled())
            pred = client.predict_element("fake_base64", "<html></html>", "Username input")
            self.assertIsNone(pred.selector)

    @patch("requests.post")
    def test_gemini_api_success_parsing(self, mock_post):
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "candidates": [{
                "content": {
                    "parts": [{
                        "text": '```json\n{"selector": "css:#email_id", "confidence": 0.95, "reasoning": "Matched email field"}\n```'
                    }]
                }
            }]
        }
        mock_response.raise_for_status.return_value = None
        mock_post.return_value = mock_response

        env = {
            "ENABLE_AI_FALLBACK": "true",
            "AI_PROVIDER": "gemini",
            "GEMINI_API_KEY": "fake_gemini_key"
        }
        with patch.dict("os.environ", env, clear=True):
            client = MultimodalVisionClient()
            self.assertTrue(client.is_enabled())
            
            pred = client.predict_element("fake_base64", "<input id='email_id'>", "Email input")
            self.assertEqual(pred.selector, "css:#email_id")
            self.assertEqual(pred.confidence, 0.95)
            self.assertEqual(pred.reasoning, "Matched email field")


if __name__ == "__main__":
    unittest.main()
