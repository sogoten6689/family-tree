from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable

import httpx

from app.hannom.client import (
    _coerce_text_list,
    get_auth_headers,
    normalize_result_bbox,
    run_image_ocr_payload,
    upload_image,
)


@dataclass
class EngineResult:
    """Kết quả OCR của 1 engine cho 1 ảnh — cùng shape với
    research/hannom-bilingual-dataset/scripts/ocr_adapters/base.py:EngineResult
    (port, không import — repo đó không phải package, đọc dữ liệu theo catalog
    file, không nhận bytes ảnh trực tiếp)."""

    engine: str
    lines: list[str]
    scores: dict[str, float] = field(default_factory=dict)
    bbox: list[dict[str, Any]] | None = None


GEMINI_OCR_PROMPT = (
    "Đây là ảnh chụp trang gia phả chữ Hán cổ. Chỉ trả về NGUYÊN VĂN chữ Hán "
    "đọc được trong ảnh, theo đúng thứ tự cột từ phải sang trái, mỗi cột 1 "
    "dòng. Không dịch nghĩa, không giải thích, không thêm ký tự nào ngoài "
    "nguyên văn Hán."
)


def run_kimhannom(
    file_bytes: bytes,
    filename: str,
    *,
    ocr_id: int | None = None,
    lang_type: int | None = None,
) -> EngineResult | None:
    """Engine duy nhất trả được bbox (xem app/hannom/client.py)."""
    try:
        headers = get_auth_headers()
        timeout = httpx.Timeout(120.0, connect=20.0)
        with httpx.Client(headers=headers, timeout=timeout) as client:
            temp_file_name = upload_image(client, file_bytes, filename)
            payload = run_image_ocr_payload(
                client,
                temp_file_name=temp_file_name,
                ocr_id=ocr_id,
                lang_type=lang_type,
            )
        lines = _coerce_text_list(payload, keys=("result_ocr_text", "ocr_text", "text"))
        if not lines:
            return None
        bbox = normalize_result_bbox(payload.get("result_bbox"))
        return EngineResult(engine="kimhannom", lines=lines, bbox=bbox)
    except Exception:
        # Lỗi API (quota/mạng/timeout) -> bỏ qua engine này, không chặn engine
        # khác hay toàn bộ request (cùng contract None-on-failure như các
        # adapter gốc trong research/hannom-bilingual-dataset).
        return None


def run_gemini_vision(file_bytes: bytes, filename: str, **_: Any) -> EngineResult | None:
    """Dùng lại đúng GOOGLE_API_KEY/GeminiClient đã cấu hình sẵn — không cần
    credential mới. Prompt đã xác nhận hoạt động thật trên ảnh Hán-Nôm, xem
    research/hannom-bilingual-dataset/scripts/ocr_adapters/gemini.py."""
    try:
        from app.config import get_llm_api_key
        from app.gemini_client import GeminiClient

        if not get_llm_api_key():
            return None
        client = GeminiClient()
        mime_type = "image/png" if filename.lower().endswith(".png") else "image/jpeg"
        text = client.generate_vision(GEMINI_OCR_PROMPT, file_bytes, mime_type=mime_type)
        lines = [line.strip() for line in (text or "").splitlines() if line.strip()]
        if not lines:
            return None
        return EngineResult(engine="gemini_vision", lines=lines)
    except Exception:
        return None


ENGINE_REGISTRY: dict[str, Callable[..., EngineResult | None]] = {
    "kimhannom": run_kimhannom,
    "gemini_vision": run_gemini_vision,
}
