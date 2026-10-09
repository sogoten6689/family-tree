from __future__ import annotations

import time
from typing import Any, Optional

from google import genai

from app.config import GEMINI_MODEL_NAME, get_google_api_key, get_llm_provider
from app.gemini_usage import record_usage, usage_from_response


class GeminiClient:
    """Thin wrapper around google-genai (same pattern as old_code/generate-family-tree).

    Mỗi lần gọi ghi số token (đầu vào / đầu ra / thinking) theo `task` vào bảng
    gemini_usage (app/gemini_usage.py) — để đo chi phí thật theo loại việc.
    """

    def __init__(self) -> None:
        # LLM_PROVIDER=ramcloud: mọi lời gọi (dựng cây, dịch, OCR vision…) đi qua RamCloud
        # với đúng giao diện này nên không phải sửa từng chỗ gọi.
        self._ramcloud = None
        if get_llm_provider() == "ramcloud":
            from app.ramcloud_client import RamCloudClient

            self._ramcloud = RamCloudClient()
            return
        api_key = get_google_api_key()
        if not api_key:
            raise ValueError(
                "GOOGLE_API_KEY is not set. Add it via Admin › Developer › Cấu hình or the environment."
            )
        self._client = genai.Client(api_key=api_key)

    def _call(self, contents: Any, *, task: str, config: Optional[Any] = None) -> str:
        started = time.monotonic()
        try:
            response = self._client.models.generate_content(
                model=GEMINI_MODEL_NAME, contents=contents, config=config
            )
        except Exception as exc:
            record_usage(
                task=task,
                model=GEMINI_MODEL_NAME,
                duration_ms=int((time.monotonic() - started) * 1000),
                ok=False,
                error=f"{type(exc).__name__}: {exc}",
            )
            raise
        record_usage(
            task=task,
            model=GEMINI_MODEL_NAME,
            duration_ms=int((time.monotonic() - started) * 1000),
            ok=True,
            **usage_from_response(response),
        )
        return response.text or ""

    def generate(
        self,
        prompt: str,
        *,
        task: str = "generic",
        json_output: bool = False,
        max_output_tokens: Optional[int] = None,
    ) -> str:
        if self._ramcloud is not None:
            return self._ramcloud.generate(
                prompt, task=task, json_output=json_output, max_output_tokens=max_output_tokens
            )
        config = None
        if json_output or max_output_tokens:
            from google.genai import types

            config = types.GenerateContentConfig(
                response_mime_type="application/json" if json_output else None,
                max_output_tokens=max_output_tokens,
            )
        return self._call(prompt, task=task, config=config)

    def generate_vision(
        self, prompt: str, image_bytes: bytes, mime_type: str = "image/jpeg", *, task: str = "ocr_vision"
    ) -> str:
        """Gọi Gemini với 1 ảnh + prompt (đọc ảnh trực tiếp, ví dụ OCR) — cùng
        cách research/hannom-bilingual-dataset/scripts/ocr_adapters/gemini.py
        đã dùng và xác nhận hoạt động thật trên ảnh Hán-Nôm."""
        if self._ramcloud is not None:
            return self._ramcloud.generate_vision(prompt, image_bytes, mime_type, task=task)
        from google.genai import types

        return self._call([types.Part.from_bytes(data=image_bytes, mime_type=mime_type), prompt], task=task)
