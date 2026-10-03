from __future__ import annotations

from typing import Optional

from app.config import get_google_api_key
from app.gemini_client import GeminiClient


def build_dich_nghia_prompt(transliteration_text: str, hannom_context: Optional[str] = None) -> str:
    context_block = (
        f"\n\nNguyên văn chữ Hán-Nôm (chỉ để tham khảo, không cần dịch lại):\n{hannom_context}"
        if hannom_context
        else ""
    )
    return (
        "Đây là văn bản gia phả chữ Hán-Việt (đã phiên âm sang Quốc ngữ, còn cổ/văn "
        "ngôn). Hãy diễn giải lại thành tiếng Việt hiện đại, dễ hiểu, giữ đúng nghĩa "
        "và tên riêng/địa danh/niên hiệu (không phiên âm lại, không thêm thông tin "
        "ngoài văn bản gốc). Chỉ trả về đúng phần diễn giải, không giải thích thêm.\n\n"
        f"Văn bản phiên âm:\n{transliteration_text}"
        f"{context_block}"
    )


def translate_to_modern_vietnamese(
    transliteration_text: str,
    hannom_context: Optional[str] = None,
) -> tuple[Optional[str], Optional[str]]:
    """Dịch nghĩa Quốc ngữ hiện đại từ bản phiên âm Hán-Việt (đã là tiếng
    Việt, chỉ cần hiện đại hoá) qua Gemini — tái dùng GOOGLE_API_KEY đã có.

    Returns (translation_text, None) khi thành công.
    (None, error_message) khi thiếu key, lỗi API hoặc input rỗng.
    """
    if not transliteration_text or not transliteration_text.strip():
        return None, "Dịch nghĩa skipped: input rỗng"
    if not get_google_api_key():
        return None, "Dịch nghĩa skipped: GOOGLE_API_KEY not set"

    try:
        client = GeminiClient()
        prompt = build_dich_nghia_prompt(transliteration_text, hannom_context)
        text = client.generate(prompt, task="translate")
        text = (text or "").strip()
        if not text:
            return None, "Gemini trả về rỗng"
        return text, None
    except Exception as exc:  # pragma: no cover - API/network
        return None, f"Gemini error: {exc}"
