#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Interface chung cho 5 OCR adapter (paddle_v6, kim_hannom_lab (=CLC), deepseek, google_vision, gemini).

Mỗi adapter chỉ có 1 hàm: load(book, stem, family_tree_root) -> EngineResult | None.
Trả None nếu engine đó KHÔNG có dữ liệu cho trang này (thiếu key, chưa chạy, ...) —
vote_ocr.py sẽ tự bỏ qua engine trả None, không chặn tiến độ.

`book` = 1 entry trong family-tree/data/00_raw/hannom/books_catalog.json (dict).
`stem` = tên trang, vd "0", "001" — tuỳ quy ước của từng cuốn trong catalog.
"""
from __future__ import annotations

import concurrent.futures
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, TypeVar

T = TypeVar("T")

# XÁC NHẬN 2026-09-12: vote_ocr.py treo hơn 10 tiếng ở nom-1158 trang 014 vì
# 1 lệnh gọi Gemini/Google Vision không có timeout riêng (khác deepseek dùng
# requests timeout=60, lab dùng httpx timeout=120.0). google-genai/google-cloud-
# vision không đảm bảo timeout mặc định hợp lý cho mọi phiên bản — bọc bằng
# thread + timeout cứng ở đây để KHÔNG BAO GIỜ treo vô hạn, thay vì tin cậy
# timeout nội bộ của từng thư viện.
#
# LƯU Ý (XÁC NHẬN 2026-09-12): KHÔNG dùng 1 executor CHUNG cố định vài luồng —
# ban đầu dùng max_workers=4 cho cả tiến trình, vô tình trở thành nút thắt cổ
# chai khi run.py/dich_nghia.py sau đó tự thêm song song nhiều trang (mọi lệnh
# gọi Gemini/Vision từ mọi trang phải xếp hàng qua đúng 4 luồng đó). Mỗi lệnh
# gọi tự tạo 1 luồng riêng, tự giải phóng ngay sau khi xong — không giới hạn
# ngược lại mức song song mà script gọi nó tự chọn.
def call_with_timeout(fn: Callable[..., T], *args: Any, timeout_s: float = 90.0, **kwargs: Any) -> T:
    with concurrent.futures.ThreadPoolExecutor(max_workers=1) as ex:
        future = ex.submit(fn, *args, **kwargs)
        return future.result(timeout=timeout_s)


@dataclass
class EngineResult:
    engine: str
    lines: list[str]
    scores: dict[str, float] = field(default_factory=dict)  # line_text -> confidence, nếu engine trả được


def pages_dir_candidates(book: dict[str, Any], family_tree_root: Path) -> list[Path]:
    """2 quy ước layout đã thấy trong catalog: nomfoundation (root/pages/) và local_scan (root/ trực tiếp)."""
    root = family_tree_root / ((book.get("paths") or {}).get("root") or "")
    pages = book.get("paths", {}).get("pages")
    candidates = []
    if pages:
        candidates.append(family_tree_root / pages)
    candidates.append(root / "pages")
    candidates.append(root)
    return candidates


def paddle_dir_candidates(book: dict[str, Any], family_tree_root: Path) -> list[Path]:
    root = family_tree_root / ((book.get("paths") or {}).get("root") or "")
    explicit = book.get("paths", {}).get("paddleocr")
    candidates = []
    if explicit:
        candidates.append(family_tree_root / explicit)
    candidates.append(root / "paddleocr")
    return candidates


def first_existing_file(candidates: list[Path], filename: str) -> Path | None:
    for d in candidates:
        p = d / filename
        if p.is_file():
            return p
    return None
