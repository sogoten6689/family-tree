"""Engine phiên âm + dịch nghĩa có sẵn của backend (đăng ký vào khe engine văn bản).

`kim_gemini` (2026-10-04): mỗi trang
  1. Kim Hán Nôm phiên âm Hán-Việt (1 lần gọi, như pipeline tải ảnh mới),
  2. Gemini dịch nghĩa Quốc ngữ hiện đại (1 lần gọi, JSON: 1 câu dịch / dòng).
Số dòng phiên âm hoặc số câu dịch không khớp số dòng chữ Hán → gộp CẢ TRANG
thành 1 câu {cn, sv, vi} (vẫn là bản dịch thật, chỉ thô hơn) — không gọi lại cho
đỡ tốn. Gemini trả không phải JSON / rỗng → báo lỗi (KHÔNG ghi câu giữ chỗ).
Chỉ gửi dòng CÓ chữ Hán, và chỉ phần chữ Hán của dòng (bỏ số trang "161",
"tờ 10b", ký hiệu "*", "O" của OCR); trang không có chữ Hán → [] (không gọi gì).

TỐN TIỀN mỗi lần chạy (Kim + Gemini theo trang; Gemini ghi vào bảng gemini_usage,
task "translate"). Thiếu tài khoản Kim / GOOGLE_API_KEY → lỗi rõ ràng, lần chạy
đánh dấu lỗi.
"""

from __future__ import annotations

import json
from typing import Any, Callable, Optional

from app.hannom.text_engines import register_text_engine
from app.hannom.vote_char import han_only

GEMINI_MAX_OUTPUT_TOKENS = 8192


def build_line_translation_prompt(items: list[tuple[str, str]]) -> str:
    numbered = "\n".join(f"{i}. [Hán] {cn}\n   [Phiên âm] {sv}" for i, (cn, sv) in enumerate(items, start=1))
    return (
        "Đây là các dòng của 1 trang gia phả chữ Hán-Nôm (văn bản OCR, có thể sai/thiếu chữ), kèm "
        "phiên âm Hán-Việt. Dịch từng dòng sang tiếng Việt hiện đại, dễ hiểu, giữ đúng nghĩa và tên "
        "riêng/địa danh/niên hiệu, không thêm thông tin ngoài văn bản.\n"
        "Quy tắc:\n"
        "- Mỗi dòng chọn MỘT cách dịch hợp lý nhất: không dùng dấu \"/\" để đưa nhiều phương án, "
        "không đặt câu hỏi, không giải thích hay bình luận.\n"
        "- Dòng là tên người/chức danh/địa danh rời → giữ dạng phiên âm viết hoa (vd \"Phan Công\").\n"
        "- Dòng không đủ nghĩa (OCR vụn, sai chữ) → dịch phần hiểu được và thêm \"(chưa rõ nghĩa)\"; "
        "nếu không hiểu gì thì ghi đúng \"(chưa rõ nghĩa)\".\n"
        f"Trả về DUY NHẤT JSON dạng {{\"vi\": [...]}} với đúng {len(items)} chuỗi, chuỗi thứ i là "
        "bản dịch của dòng i, không để trống.\n\n"
        f"{numbered}"
    )


def _parse_vi_list(raw: str) -> Optional[list[str]]:
    """Danh sách câu dịch không rỗng từ JSON {"vi": [...]} (hoặc mảng trần); None nếu hỏng."""
    try:
        data = json.loads(raw)
    except (TypeError, ValueError):
        return None
    values = data.get("vi") if isinstance(data, dict) else data
    if not isinstance(values, list):
        return None
    texts = [str(v).strip() for v in values if str(v).strip()]
    return texts or None


def _default_transliterate(text: str) -> list[str]:
    import httpx

    from app.hannom.client import get_auth_headers, run_transliteration

    timeout = httpx.Timeout(120.0, connect=20.0)
    with httpx.Client(headers=get_auth_headers(), timeout=timeout) as client:
        return run_transliteration(client, text=text)


def _default_translate(prompt: str) -> str:
    from app.config import get_google_api_key
    from app.gemini_client import GeminiClient

    if not get_google_api_key():
        raise RuntimeError("Chưa cấu hình GOOGLE_API_KEY (Admin › Cấu hình) — không dịch nghĩa được.")
    return GeminiClient().generate(prompt, task="translate", json_output=True, max_output_tokens=GEMINI_MAX_OUTPUT_TOKENS)


def kim_gemini_engine(
    hannom_text: str,
    *,
    page_number: int,
    transliterate: Callable[[str], list[str]] = _default_transliterate,
    translate: Callable[[str], str] = _default_translate,
) -> list[dict[str, Any]]:
    lines = [han for han in (han_only(line) for line in (hannom_text or "").splitlines()) if han]
    if not lines:  # chỉ số trang / ký hiệu → không tốn lần gọi nào
        return []
    sv_lines = [s.strip() for s in transliterate("\n".join(lines)) if s and s.strip()]
    if not sv_lines:
        raise RuntimeError(f"trang {page_number}: Kim Hán Nôm không trả về phiên âm.")
    if len(sv_lines) == len(lines):
        items = list(zip(lines, sv_lines))
    else:  # Kim gộp/tách dòng khác → không ghép được từng dòng
        items = [(" ".join(lines), " ".join(sv_lines))]
    vi = _parse_vi_list(translate(build_line_translation_prompt(items)))
    if vi is None:
        raise RuntimeError(f"trang {page_number}: Gemini không trả JSON bản dịch hợp lệ — chạy lại sau.")
    if len(vi) != len(items):  # sai số câu → gộp cả trang (bản dịch thật, thô hơn)
        return [{"cn": " ".join(lines), "sv": " ".join(sv_lines), "vi": " ".join(vi)}]
    return [{"cn": cn, "sv": sv, "vi": v} for (cn, sv), v in zip(items, vi)]


register_text_engine("kim_gemini", kim_gemini_engine)
