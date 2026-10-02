"""Mẫu adapter engine phiên âm/dịch nghĩa.

Cách dùng: chép file này thành `text_engines_local.py` (cùng thư mục), thay
phần thân hàm bằng lời gọi tool của bạn, rồi khởi động lại backend. Backend tự
nạp file đó lúc khởi động (app/hannom/text_engines.py:load_local_engines) —
nếu file lỗi, lỗi hiện ở Admin › Cấu hình › "Engine phiên âm / dịch nghĩa".

Hợp đồng của 1 engine:
- Input: văn bản Hán Nôm của 1 trang (`hannom_text`) + `page_number`.
- Output: list các câu `{"cn": chữ Hán, "sv": phiên âm, "vi": dịch nghĩa}`
  (không cần trường `page` — runner tự gắn). Thiếu trường/rỗng → cả lần chạy
  bị đánh lỗi; câu chứa "[Chú giải]" bị bỏ qua.
- Chạy nền, tuần tự từng trang; mỗi trang tối đa 600s
  (text_engine_runner.DEFAULT_PAGE_TIMEOUT_SECONDS). Exception = lần chạy lỗi,
  thông báo hiện ở cột "Chạy" trong tab "Phiên bản & nhập LLM".
"""

from __future__ import annotations

from app.hannom.text_engines import register_text_engine


def echo_engine(hannom_text: str, *, page_number: int) -> list[dict[str, str]]:
    """Engine thử luồng chạy — không gọi dịch vụ nào, mỗi dòng thành 1 câu."""
    return [
        {"cn": line, "sv": f"(phiên âm trang {page_number})", "vi": f"(dịch nghĩa trang {page_number})"}
        for line in hannom_text.splitlines()
        if line.strip()
    ]


register_text_engine("echo", echo_engine)
