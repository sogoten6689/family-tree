from __future__ import annotations

import re
import unicodedata
from collections import Counter
from dataclasses import dataclass, field
from typing import Any

# Nhập kết quả {cn, sv, vi} do tool LLM (TOOL_ChatGPT_API / TOOL_Gemini_API,
# chạy trên máy người dùng) sinh ra — web chỉ nhận DỮ LIỆU, không chạy tool.
# Mỗi lần nhập = 1 gia_pha_version mới (cha = version hiện tại), không ghi
# đè kết quả Kim Hán Nôm, chờ admin duyệt trước khi vào dữ liệu train.

SOURCE_PATTERN = re.compile(r"^[a-z0-9][a-z0-9_-]{0,63}$")
ANNOTATION_MARK = "[Chú giải]"
# Dưới ngưỡng này: cảnh báo (không chặn) — OCR có thể sai nên không ép khớp.
MIN_CN_COVERAGE = 0.8
MAX_ERRORS_REPORTED = 20


@dataclass
class ImportRecord:
    page: int
    cn: str
    sv: str
    vi: str


@dataclass
class ParsedImport:
    source: str
    model_note: str | None
    pages: dict[int, list[ImportRecord]] = field(default_factory=dict)
    skipped_annotations: int = 0
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    @property
    def record_count(self) -> int:
        return sum(len(records) for records in self.pages.values())


def _is_text(value: Any) -> bool:
    return isinstance(value, str) and value.strip() != ""


def parse_import(payload: dict[str, Any], known_pages: set[int]) -> ParsedImport:
    """Kiểm tra payload `{source, model_note?, records: [{page, cn, sv, vi}]}`.
    Lỗi (errors) → không được nhập; cảnh báo (warnings) chỉ để người dùng biết."""
    source = str(payload.get("source") or "").strip()
    note_raw = payload.get("model_note")
    result = ParsedImport(source=source, model_note=str(note_raw).strip()[:255] if note_raw else None)

    if not SOURCE_PATTERN.match(source):
        result.errors.append("`source` phải là chữ thường/số/-/_ (vd. chatgpt-web, gemini-web).")
    records = payload.get("records")
    if not isinstance(records, list) or not records:
        result.errors.append("`records` phải là danh sách khác rỗng.")
        return result

    for index, raw in enumerate(records):
        if len(result.errors) >= MAX_ERRORS_REPORTED:
            result.errors.append("… còn lỗi khác, đã dừng liệt kê.")
            break
        where = f"records[{index}]"
        if not isinstance(raw, dict):
            result.errors.append(f"{where}: phải là object.")
            continue
        page = raw.get("page")
        if isinstance(page, bool) or not isinstance(page, int):
            result.errors.append(f"{where}: `page` phải là số nguyên.")
            continue
        if page not in known_pages:
            result.errors.append(f"{where}: trang {page} không tồn tại trong bộ gia phả.")
            continue
        missing = [key for key in ("cn", "sv", "vi") if not _is_text(raw.get(key))]
        if missing:
            result.errors.append(f"{where}: thiếu {', '.join(missing)}.")
            continue
        cn, sv, vi = raw["cn"].strip(), raw["sv"].strip(), raw["vi"].strip()
        if ANNOTATION_MARK in cn or ANNOTATION_MARK in sv or ANNOTATION_MARK in vi:
            result.skipped_annotations += 1
            continue
        result.pages.setdefault(page, []).append(ImportRecord(page=page, cn=cn, sv=sv, vi=vi))

    if not result.errors and not result.pages:
        result.errors.append("Không còn câu nào sau khi bỏ các câu [Chú giải].")
    return result


def _han_chars(text: str) -> Counter[str]:
    """Chỉ đếm chữ (bỏ khoảng trắng, dấu câu) — so khớp theo code point."""
    return Counter(ch for ch in text if not ch.isspace() and not unicodedata.category(ch).startswith("P"))


def cn_coverage(cn_texts: list[str], ocr_text: str | None) -> float | None:
    """Tỉ lệ chữ trong các câu `cn` có mặt trong văn bản OCR của trang
    (đếm theo bội số). None nếu trang chưa có OCR để đối chiếu."""
    if not ocr_text:
        return None
    wanted = _han_chars("".join(cn_texts))
    total = sum(wanted.values())
    if total == 0:
        return None
    available = _han_chars(ocr_text)
    matched = sum(min(count, available[ch]) for ch, count in wanted.items())
    return matched / total


def add_coverage_warnings(parsed: ParsedImport, ocr_by_page: dict[int, str | None]) -> None:
    for page, records in sorted(parsed.pages.items()):
        coverage = cn_coverage([r.cn for r in records], ocr_by_page.get(page))
        if coverage is None:
            parsed.warnings.append(f"Trang {page}: chưa có văn bản OCR để đối chiếu chữ Hán.")
        elif coverage < MIN_CN_COVERAGE:
            parsed.warnings.append(
                f"Trang {page}: chỉ {coverage:.0%} chữ Hán của `cn` khớp văn bản OCR — kiểm tra lại đúng trang chưa."
            )
