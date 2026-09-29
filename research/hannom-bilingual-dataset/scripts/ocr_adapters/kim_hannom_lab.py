#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Adapter — đọc kết quả Kim Hán Nôm Lab (= "CLC" trong tên gọi cũ ở họp trước —
XÁC NHẬN 2026-09-08: 1 dịch vụ, không phải 2 engine riêng) đã CÓ SẴN trong
family-tree (không gọi API mới).

Đọc `{stem}-ocr-raw.json` (trường result_ocr_text) + `{stem}-boundingbox.json`
(trường result_bbox, để lấy confidence) — đúng format ocr_lab_hannom_catalog.py
đã ghi. Không tự OCR lại; nếu thiếu file thì trả None (bỏ qua ở vote_ocr.py).
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .base import EngineResult, pages_dir_candidates, first_existing_file

ENGINE_NAME = "kim_hannom_lab"


def load(book: dict[str, Any], stem: str, family_tree_root: Path) -> EngineResult | None:
    candidates = pages_dir_candidates(book, family_tree_root)
    raw_path = first_existing_file(candidates, f"{stem}-ocr-raw.json")
    if raw_path is None:
        return None
    try:
        raw = json.loads(raw_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    lines = [str(t).strip() for t in (raw.get("result_ocr_text") or []) if str(t).strip()]
    if not lines:
        return None

    scores: dict[str, float] = {}
    bbox_path = first_existing_file(candidates, f"{stem}-boundingbox.json")
    if bbox_path is not None:
        try:
            bbox = json.loads(bbox_path.read_text(encoding="utf-8"))
            for entry in bbox.get("result_bbox") or []:
                try:
                    _, (text, score) = entry
                except (ValueError, TypeError):
                    continue
                scores[str(text)] = max(scores.get(str(text), 0.0), float(score))
        except (OSError, json.JSONDecodeError, TypeError, ValueError):
            pass

    return EngineResult(engine=ENGINE_NAME, lines=lines, scores=scores)
