from __future__ import annotations

from google import genai

from app.config import GEMINI_MODEL_NAME, get_google_api_key


class GeminiClient:
    """Thin wrapper around google-genai (same pattern as old_code/generate-family-tree)."""

    def __init__(self) -> None:
        api_key = get_google_api_key()
        if not api_key:
            raise ValueError(
                "GOOGLE_API_KEY is not set. Add it via Admin › Developer › Cấu hình or the environment."
            )
        self._client = genai.Client(api_key=api_key)

    def generate(self, prompt: str) -> str:
        response = self._client.models.generate_content(
            model=GEMINI_MODEL_NAME,
            contents=prompt,
        )
        return response.text or ""
