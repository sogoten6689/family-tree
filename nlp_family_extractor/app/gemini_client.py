from __future__ import annotations

from google import genai

from app.config import GEMINI_MODEL_NAME, GOOGLE_API_KEY


class GeminiClient:
    """Thin wrapper around google-genai (same pattern as old_code/generate-family-tree)."""

    def __init__(self) -> None:
        if not GOOGLE_API_KEY:
            raise ValueError("GOOGLE_API_KEY is not set. Add it to .env or the environment.")
        self._client = genai.Client(api_key=GOOGLE_API_KEY)

    def generate(self, prompt: str) -> str:
        response = self._client.models.generate_content(
            model=GEMINI_MODEL_NAME,
            contents=prompt,
        )
        return response.text or ""
