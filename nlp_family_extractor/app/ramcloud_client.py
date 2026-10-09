from __future__ import annotations

import base64
import time
from typing import Any, Optional

import httpx

from app.config import get_ramcloud_base_url, get_ramcloud_key, get_ramcloud_model
from app.gemini_usage import record_usage

# Cloudflare của RamCloud chặn User-Agent mặc định của thư viện HTTP (HTTP 403,
# error code 1010) → gửi UA trình duyệt. Xem ghi chú RamCloud (07/10/2026).
_BROWSER_UA = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"
)


class RamCloudError(RuntimeError):
    """Lỗi gọi RamCloud. Thông điệp KHÔNG chứa khoá API."""


class RamCloudClient:
    """Bộ gọi RamCloud (API kiểu OpenAI /chat/completions) có cùng giao diện với
    GeminiClient: generate() và generate_vision(). Mỗi lần gọi ghi usage theo task
    (cùng bảng gemini_usage) để đo chi phí. Khoá đọc từ setting RAMCLOUD_KEY."""

    def __init__(self, *, transport: Optional[httpx.BaseTransport] = None, timeout: float = 120.0) -> None:
        key = get_ramcloud_key()
        if not key:
            raise ValueError("RAMCLOUD_KEY is not set. Add it via Admin › Developer › Cấu hình or the environment.")
        self._model = get_ramcloud_model()
        self._url = f"{get_ramcloud_base_url()}/chat/completions"
        self._http = httpx.Client(
            timeout=httpx.Timeout(timeout, connect=20.0),
            transport=transport,
            headers={"Authorization": f"Bearer {key}", "User-Agent": _BROWSER_UA, "Content-Type": "application/json"},
        )

    @staticmethod
    def _usage(body: dict[str, Any]) -> dict[str, Any]:
        usage = body.get("usage") or {}
        details = usage.get("completion_tokens_details") or {}
        cached = (usage.get("prompt_tokens_details") or {}).get("cached_tokens") or 0
        choices = body.get("choices") or [{}]
        finish = choices[0].get("finish_reason")
        return {
            "prompt_tokens": int(usage.get("prompt_tokens") or 0),
            "output_tokens": int(usage.get("completion_tokens") or 0),
            "thinking_tokens": int(details.get("reasoning_tokens") or 0),
            "cached_tokens": int(cached),
            "total_tokens": int(usage.get("total_tokens") or 0),
            "finish_reason": str(finish)[:32] if finish else None,
        }

    def _chat(
        self,
        messages: list[dict[str, Any]],
        *,
        task: str,
        json_output: bool = False,
        max_output_tokens: Optional[int] = None,
    ) -> str:
        payload: dict[str, Any] = {"model": self._model, "messages": messages}
        if json_output:
            payload["response_format"] = {"type": "json_object"}
        if max_output_tokens:
            payload["max_tokens"] = max_output_tokens
        started = time.monotonic()
        try:
            response = self._http.post(self._url, json=payload)
            if response.status_code >= 400:
                raise RamCloudError(f"RamCloud HTTP {response.status_code}: {response.text[:200]}")
            body = response.json()
        except Exception as exc:
            record_usage(
                task=task,
                model=self._model,
                duration_ms=int((time.monotonic() - started) * 1000),
                ok=False,
                error=f"{type(exc).__name__}: {exc}",
            )
            raise
        record_usage(
            task=task,
            model=self._model,
            duration_ms=int((time.monotonic() - started) * 1000),
            ok=True,
            **self._usage(body),
        )
        choices = body.get("choices") or []
        content = (choices[0].get("message") or {}).get("content") if choices else None
        return content or ""

    def generate(
        self,
        prompt: str,
        *,
        task: str = "generic",
        json_output: bool = False,
        max_output_tokens: Optional[int] = None,
    ) -> str:
        return self._chat(
            [{"role": "user", "content": prompt}],
            task=task,
            json_output=json_output,
            max_output_tokens=max_output_tokens,
        )

    def generate_vision(
        self, prompt: str, image_bytes: bytes, mime_type: str = "image/jpeg", *, task: str = "ocr_vision"
    ) -> str:
        data_url = f"data:{mime_type};base64,{base64.b64encode(image_bytes).decode('ascii')}"
        return self._chat(
            [
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": prompt},
                        {"type": "image_url", "image_url": {"url": data_url}},
                    ],
                }
            ],
            task=task,
        )
