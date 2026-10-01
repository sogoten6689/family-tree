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

    def generate_vision(self, prompt: str, image_bytes: bytes, mime_type: str = "image/jpeg") -> str:
        """Gọi Gemini với 1 ảnh + prompt (đọc ảnh trực tiếp, ví dụ OCR) — cùng
        cách research/hannom-bilingual-dataset/scripts/ocr_adapters/gemini.py
        đã dùng và xác nhận hoạt động thật trên ảnh Hán-Nôm."""
        from google.genai import types

        response = self._client.models.generate_content(
            model=GEMINI_MODEL_NAME,
            contents=[types.Part.from_bytes(data=image_bytes, mime_type=mime_type), prompt],
        )
        return response.text or ""
