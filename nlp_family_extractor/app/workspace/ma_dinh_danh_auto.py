from __future__ import annotations

import json
import re
from typing import Any, Callable, Optional

from app.workspace.ma_dinh_danh import HINH_THUC_VALUES, QUY_MO_VALUES, ho_code_for, letter_for, slugify_dia_danh

# Trích 5 thông tin để tự tạo mã định danh từ văn bản gia phả (bản dịch
# nghĩa Quốc ngữ) bằng Gemini. `generate` truyền vào từ ngoài (test dùng hàm
# giả — không gọi Gemini thật; mỗi lần gọi thật tốn tiền = R3).

MAX_TEXT_CHARS = 30000
MIN_YEAR, MAX_YEAR = 100, 2100

Generate = Callable[[str], str]


def build_prompt(text: str) -> str:
    return f"""Bạn là chuyên gia gia phả học Hán Nôm. Đọc văn bản gia phả (bản dịch tiếng Việt) dưới đây và trả về DUY NHẤT 1 object JSON, không giải thích:
{{"quy_mo": ..., "hinh_thuc": ..., "ho": ..., "dia_danh_ngan": ..., "nam_soan_goc": ...}}

- quy_mo: đúng 1 trong {json.dumps(QUY_MO_VALUES, ensure_ascii=False)}
- hinh_thuc: đúng 1 trong {json.dumps(HINH_THUC_VALUES, ensure_ascii=False)} (Bộ = sách có đủ đồ + ký; Đồ = sơ đồ; Ký = văn ký thuật; Điệp = bản kê ngắn)
- ho: họ của dòng họ, viết có dấu (vd "Nguyễn", "Phan")
- dia_danh_ngan: địa danh CẤP THẤP NHẤT có tên nơi dòng họ cư trú/thuỷ tổ (làng/thôn/xã), có dấu, không kèm cấp hành chính (vd "Gia Thiện", không phải "xã Thạch Châu, Hà Tĩnh")
- nam_soan_goc: năm dương lịch soạn BẢN GỐC (số nguyên), KHÔNG lấy năm sao chép/in lại/dịch; quy đổi niên hiệu nếu cần
- Trường nào văn bản không đủ căn cứ thì để null — không đoán.

Văn bản:
{text[:MAX_TEXT_CHARS]}
"""


def parse_response(raw: str) -> tuple[Optional[dict[str, Any]], list[str]]:
    """Kiểm tra câu trả lời của Gemini. Trả về (5 input hợp lệ, []) hoặc
    (None, danh sách lý do) — thiếu/sai bất kỳ trường nào thì KHÔNG tạo mã."""
    match = re.search(r"\{.*\}", raw or "", re.DOTALL)
    if not match:
        return None, ["Gemini không trả về JSON."]
    try:
        data = json.loads(match.group())
    except json.JSONDecodeError:
        return None, ["JSON của Gemini không hợp lệ."]
    problems: list[str] = []
    quy_mo, hinh_thuc = data.get("quy_mo"), data.get("hinh_thuc")
    if quy_mo not in QUY_MO_VALUES:
        problems.append(f"quy_mo {quy_mo!r} không thuộc {QUY_MO_VALUES}")
    if hinh_thuc not in HINH_THUC_VALUES:
        problems.append(f"hinh_thuc {hinh_thuc!r} không thuộc {HINH_THUC_VALUES}")
    if quy_mo in QUY_MO_VALUES and hinh_thuc in HINH_THUC_VALUES and letter_for(quy_mo, hinh_thuc) is None:
        problems.append(f"không có chữ mã cho ({quy_mo}, {hinh_thuc})")
    ho = data.get("ho")
    if not isinstance(ho, str) or not ho.strip() or ho_code_for(ho.strip()) is None:
        problems.append(f"ho {ho!r} không hợp lệ")
    dia_danh = data.get("dia_danh_ngan")
    if not isinstance(dia_danh, str) or not slugify_dia_danh(dia_danh):
        problems.append(f"dia_danh_ngan {dia_danh!r} không hợp lệ")
    nam = data.get("nam_soan_goc")
    if isinstance(nam, str) and nam.strip().isdigit():
        nam = int(nam.strip())
    if isinstance(nam, bool) or not isinstance(nam, int) or not MIN_YEAR <= nam <= MAX_YEAR:
        problems.append(f"nam_soan_goc {data.get('nam_soan_goc')!r} không hợp lệ")
    if problems:
        return None, problems
    return {
        "quy_mo": quy_mo,
        "hinh_thuc": hinh_thuc,
        "ho_toc": ho.strip(),
        "dia_danh_ngan": dia_danh.strip(),
        "nam_soan_goc": nam,
    }, []


def extract_identifier_inputs(text: str, generate: Generate) -> tuple[Optional[dict[str, Any]], list[str]]:
    if not text or not text.strip():
        return None, ["Chưa có văn bản (dịch nghĩa/phiên âm) để trích thông tin."]
    try:
        raw = generate(build_prompt(text))
    except Exception as error:  # noqa: BLE001 — lỗi mạng/key của Gemini
        return None, [f"Gọi Gemini lỗi: {error}"]
    return parse_response(raw)


def default_generate() -> Generate:
    from app.gemini_client import GeminiClient

    return GeminiClient().generate


def ensure_ma_dinh_danh(scans: Any, scan: Any, generate: Optional[Generate] = None) -> tuple[Any, list[str]]:
    """Scan chưa có mã → trích 5 input từ bản dịch (hoặc phiên âm) bằng
    Gemini rồi tự tạo mã (nguồn "gemini"). Đã có mã → giữ nguyên, không gọi
    Gemini. Trả về (scan, lý do nếu chưa tạo được)."""
    if scan.ma_dinh_danh:
        return scan, []
    text = scan.source_text or scan.transliteration_text or ""
    # Khởi tạo client lười: thiếu GOOGLE_API_KEY thì lỗi đi qua nhánh "Gọi
    # Gemini lỗi" của extract_identifier_inputs, không văng ra ngoài.
    gen = generate or (lambda prompt: default_generate()(prompt))
    inputs, problems = extract_identifier_inputs(text, gen)
    if inputs is None:
        return scan, problems
    try:
        return scans.auto_assign_ma_dinh_danh(scan, inputs, nguon="gemini"), []
    except ValueError as error:
        return scan, [str(error)]
