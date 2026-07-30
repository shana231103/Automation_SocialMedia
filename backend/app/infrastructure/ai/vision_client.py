# File: backend/app/infrastructure/ai/vision_client.py
"""Vision LLM Client for Computer Vision and DOM-based element detection."""

import os
import json
import logging
from abc import ABC, abstractmethod
from typing import Optional
import requests
from pydantic import BaseModel

logger = logging.getLogger(__name__)


class ElementPrediction(BaseModel):
    """Prediction result containing suggested CSS/XPath selector and confidence score."""
    selector: Optional[str] = None
    confidence: float = 0.0
    reasoning: str = ""


class VisionClient(ABC):
    """Abstract interface for AI Vision Multimodal LLM Clients."""

    @abstractmethod
    def predict_element(self, image_base64: str, dom_snippet: str, hint_text: str) -> ElementPrediction:
        """
        Analyze screenshot and DOM snippet to predict target element selector.

        Args:
            image_base64: Base64-encoded PNG screenshot.
            dom_snippet: Filtered interactable HTML DOM snippet.
            hint_text: Description of target element (e.g. 'Email/Username input').

        Returns:
            ElementPrediction DTO containing predicted selector and confidence.
        """
        pass

    @abstractmethod
    def is_enabled(self) -> bool:
        """Return True if AI Vision Fallback is enabled in environment settings."""
        pass


class MultimodalVisionClient(VisionClient):
    """Production implementation of VisionClient using Google Gemini / OpenAI REST APIs."""

    def __init__(self):
        self.provider = os.getenv("AI_PROVIDER", "gemini").lower()
        self.enabled = os.getenv("ENABLE_AI_FALLBACK", "false").lower() in ("true", "1", "yes")
        self.gemini_key = os.getenv("GEMINI_API_KEY", "")
        self.openai_key = os.getenv("OPENAI_API_KEY", "")

    def is_enabled(self) -> bool:
        return self.enabled and bool(self.gemini_key or self.openai_key or self.provider == "ollama")

    def predict_element(self, image_base64: str, dom_snippet: str, hint_text: str) -> ElementPrediction:
        if not self.is_enabled():
            return ElementPrediction(reasoning="AI Fallback disabled or missing API credentials.")

        prompt = (
            f"Analyze the webpage screenshot and DOM snippet to locate the following element: '{hint_text}'.\n"
            f"DOM Snippet:\n{dom_snippet}\n\n"
            f"Respond ONLY with a JSON object in this exact format: "
            f'{{"selector": "css_or_xpath_selector", "confidence": 0.95, "reasoning": "brief explanation"}}'
        )

        try:
            if self.provider == "gemini" and self.gemini_key:
                return self._call_gemini_api(prompt, image_base64)
            elif self.provider == "openai" and self.openai_key:
                return self._call_openai_api(prompt, image_base64)
            else:
                return ElementPrediction(reasoning=f"Unsupported or unconfigured provider '{self.provider}'.")
        except Exception as e:
            logger.warning(f"AI Vision Client error: {str(e)}")
            return ElementPrediction(reasoning=f"AI Vision Client exception: {str(e)}")

    def _call_gemini_api(self, prompt: str, image_base64: str) -> ElementPrediction:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={self.gemini_key}"
        payload = {
            "contents": [{
                "parts": [
                    {"text": prompt},
                    {"inline_data": {"mime_type": "image/png", "data": image_base64}}
                ]
            }]
        }
        res = requests.post(url, json=payload, timeout=10)
        res.raise_for_status()
        data = res.json()
        
        candidates = data.get("candidates", [])
        if candidates and "content" in candidates[0]:
            text_response = candidates[0]["content"]["parts"][0].get("text", "")
            return self._parse_json_prediction(text_response)
            
        return ElementPrediction(reasoning="Empty response candidate from Gemini Vision API.")

    def _call_openai_api(self, prompt: str, image_base64: str) -> ElementPrediction:
        url = "https://api.openai.com/v1/chat/completions"
        headers = {"Authorization": f"Bearer {self.openai_key}"}
        payload = {
            "model": "gpt-4o-mini",
            "response_format": {"type": "json_object"},
            "messages": [{
                "role": "user",
                "content": [
                    {"type": "text", "text": prompt},
                    {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{image_base64}"}}
                ]
            }]
        }
        res = requests.post(url, headers=headers, json=payload, timeout=10)
        res.raise_for_status()
        data = res.json()
        text_response = data["choices"][0]["message"]["content"]
        return self._parse_json_prediction(text_response)

    def _parse_json_prediction(self, text: str) -> ElementPrediction:
        # Strip markdown json code block fences if present
        clean_text = text.strip()
        if clean_text.startswith("```"):
            clean_text = clean_text.split("\n", 1)[-1].rsplit("```", 1)[0].strip()

        try:
            parsed = json.loads(clean_text)
            return ElementPrediction(
                selector=parsed.get("selector"),
                confidence=float(parsed.get("confidence", 0.0)),
                reasoning=parsed.get("reasoning", "")
            )
        except Exception:
            return ElementPrediction(reasoning=f"Failed to parse LLM response: {text[:100]}")
