#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Adapter — đọc kết quả PaddleOCR v6 đã CÓ SẴN trong family-tree (không OCR lại).

Đọc `{stem}-paddleocr.txt` (1 dòng chữ / dòng file). Không có confidence per-line
trong .txt — nếu cần điểm, có thể mở rộng đọc `.json` cùng thư mục (chưa cần cho MVP).
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

from .base import EngineResult, paddle_dir_candidates, first_existing_file

ENGINE_NAME = "paddle_v6"


def load(book: dict[str, Any], stem: str, family_tree_root: Path) -> EngineResult | None:
    candidates = paddle_dir_candidates(book, family_tree_root)
    txt_path = first_existing_file(candidates, f"{stem}-paddleocr.txt")
    if txt_path is None:
        return None
    lines = [ln.strip() for ln in txt_path.read_text(encoding="utf-8").splitlines() if ln.strip()]
    if not lines:
        return None
    return EngineResult(engine=ENGINE_NAME, lines=lines, scores={})
