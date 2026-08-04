# File: backend/tests/unit/ai/test_ollama_status_verifier.py
"""Unit tests for the local-only Ollama account status adapter."""

import json
import threading
import unittest
from unittest.mock import MagicMock

import requests

from app.application.status_verification import StatusVerificationEvidence, VerificationFailureCode
from app.domain.models import LoginStatus, Platform
from app.infrastructure.ai.ollama_status_verifier import OllamaStatusVerifier


class OllamaStatusVerifierTests(unittest.TestCase):
    def setUp(self) -> None:
        self.session = MagicMock()
        self.verifier = OllamaStatusVerifier(http_session=self.session)
        self.evidence = StatusVerificationEvidence(
            platform=Platform.FACEBOOK,
            preliminary_status=LoginStatus.CHECKPOINT,
            sanitized_url="https://www.facebook.com/checkpoint",
            screenshot_base64="ZmFrZQ==",
            dom_snippet='<div role="main">',
        )

    def response(self, status: int = 200, content: dict | None = None, text: str = "") -> MagicMock:
        response = MagicMock()
        response.status_code = status
        response.is_redirect = False
        response.text = text
        response.content = b"{}"
        response.json.return_value = content or {}
        return response

    def test_valid_structured_response_and_request_contract(self):
        wire = {
            "status": "checkpoint", "confidence": 0.91,
            "reasoning": "Challenge UI detected", "agreement": True,
            "visual_evidence": ["challenge panel"], "dom_evidence": ["checkpoint route"],
        }
        self.session.post.return_value = self.response(content={"message": {"content": json.dumps(wire)}})

        result = self.verifier.verify(self.evidence)

        self.assertEqual(result.status, LoginStatus.CHECKPOINT)
        self.assertEqual(result.confidence, 0.91)
        url = self.session.post.call_args.args[0]
        payload = self.session.post.call_args.kwargs["json"]
        self.assertEqual(url, "http://127.0.0.1:11434/api/chat")
        self.assertEqual(payload["model"], "qwen3.5:9b")
        self.assertFalse(payload["stream"])
        self.assertIn("Use checkpoint for CAPTCHA", payload["messages"][0]["content"])
        self.assertIn("MUST return checkpoint", payload["messages"][0]["content"])
        self.assertFalse(payload["think"])
        self.assertEqual(payload["options"]["num_predict"], 256)
        self.assertEqual(payload["messages"][0]["images"], ["ZmFrZQ=="])
    def test_checkpoint_page_corrects_inconsistent_model_status(self):
        wire = {
            "status": "logged_in", "confidence": 0.95,
            "reasoning": "Incorrect model conclusion", "agreement": True,
            "visual_evidence": ["checkpoint panel"], "dom_evidence": ["checkpoint route"],
        }
        self.session.post.return_value = self.response(
            content={"message": {"content": json.dumps(wire)}},
        )

        result = self.verifier.verify(self.evidence)

        self.assertEqual(result.status, LoginStatus.CHECKPOINT)
        self.assertIn("corrected an inconsistent AI status", result.reasoning)

    def test_rejects_non_loopback_endpoint(self):
        with self.assertRaisesRegex(ValueError, "loopback"):
            OllamaStatusVerifier(base_url="https://example.com")

    def test_timeout_preserves_typed_failure(self):
        self.session.post.side_effect = requests.Timeout()
        result = self.verifier.verify(self.evidence)
        self.assertEqual(result.failure_code, VerificationFailureCode.TIMEOUT)

    def test_missing_model_and_non_vision_failures_are_distinct(self):
        self.session.post.return_value = self.response(404, text="model not found")
        missing = self.verifier.verify(self.evidence)
        self.assertEqual(missing.failure_code, VerificationFailureCode.MODEL_MISSING)

        self.session.post.return_value = self.response(400, text="model does not support images")
        unsupported = self.verifier.verify(self.evidence)
        self.assertEqual(unsupported.failure_code, VerificationFailureCode.VISION_UNSUPPORTED)

    def test_malformed_or_oversized_response_falls_back(self):
        malformed_response = self.response(content={"message": {"content": "not-json"}})
        self.session.post.return_value = malformed_response
        self.assertEqual(
            self.verifier.verify(self.evidence).failure_code,
            VerificationFailureCode.INVALID_RESPONSE,
        )

        oversized = self.response(content={})
        oversized.content = b"x" * 65537
        self.session.post.return_value = oversized
        self.assertEqual(
            self.verifier.verify(self.evidence).failure_code,
            VerificationFailureCode.INVALID_RESPONSE,
        )

    def test_pre_cancelled_request_never_calls_http(self):
        cancellation = threading.Event()
        cancellation.set()
        result = self.verifier.verify(self.evidence, cancellation)
        self.assertEqual(result.failure_code, VerificationFailureCode.CANCELLED)
        self.session.post.assert_not_called()

    def test_health_reports_installed_vision_model(self):
        self.session.post.return_value = self.response(content={"capabilities": ["completion", "vision"]})
        health = self.verifier.get_status()
        self.assertTrue(health.reachable)
        self.assertTrue(health.vision_capable)


if __name__ == "__main__":
    unittest.main()
