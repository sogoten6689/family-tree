#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Adapter — đọc kết quả PaddleOCR v6 đã CÓ SẴN trong family-tree (không OCR lại).

Ưu tiên `{stem}-paddleocr.json` (có toạ độ khung `result_bbox`) và SẮP LẠI theo
thứ tự đọc chữ Hán dọc: cột phải → trái, trong cùng cột trên → dưới. Không có
.json thì đọc `{stem}-paddleocr.txt` (1 dòng chữ / dòng file) như trước.

XÁC NHẬN 2026-10-03 (đối chiếu ảnh nom-1255 tr.1 + toạ độ khung): PaddleOCR trả
dòng theo mép TRÊN của khung (kiểu chữ ngang), nên với chữ dọc các cột bị XÁO
TRỘN — chỉ 14/1.059 trang đúng thứ tự. Sắp theo cột: độ giống cả trang với
kim_hannom_lab/deepseek tăng 0,13 → 0,64 (924 trang tốt lên). 22 trang kém đi
đều là trang phả đồ (世系圖, ô lưới) — vốn không có 1 thứ tự đọc tuyến tính.
Phân tích: scripts/analyze_vote_alignment.py.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Sequence

from .base import EngineResult, paddle_dir_candidates, first_existing_file

ENGINE_NAME = "paddle_v6"

# 2 khung cùng cột khi phần chồng nhau theo trục x > tỉ lệ này × bề rộng khung hẹp hơn.
COLUMN_OVERLAP = 0.5
# 2 khung trong cùng cột là "song song" khi chồng nhau theo trục y > tỉ lệ này × chiều cao khung thấp hơn.
SIDE_BY_SIDE_OVERLAP = 0.5


def column_order(boxes: Sequence[tuple[Sequence[Sequence[float]], str, float | None]]) -> list[tuple[str, float | None]]:
    """[(text, score)] theo thứ tự đọc — xem column_order_indices."""
    return [(boxes[i][1].strip(), boxes[i][2]) for i in column_order_indices(boxes)]


def column_order_indices(boxes: Sequence[tuple[Sequence[Sequence[float]], str, float | None]]) -> list[int]:
    """Chỉ số các khung trong `boxes` theo thứ tự đọc chữ Hán dọc.

    `boxes` = [(polygon [[x, y], ...], text, score)]. Gom khung chồng nhau theo
    trục x thành cột (1 cột có thể bị Paddle tách thành nhiều khung dọc), cột
    xếp theo tâm x giảm dần (phải → trái), trong cột xếp theo mép trên (trên →
    dưới) — khung song song cùng khoảng y đọc phải → trái. Bỏ khung rỗng.
    """
    items = []
    for index, (poly, text, score) in enumerate(boxes):
        if not (text or "").strip():
            continue
        xs = [float(p[0]) for p in poly]
        ys = [float(p[1]) for p in poly]
        items.append((min(xs), max(xs), min(ys), text.strip(), score, max(ys), index))
    # Khoá phụ (y, chữ, x) để kết quả không phụ thuộc thứ tự đầu vào khi tâm x trùng nhau.
    items.sort(key=lambda b: (-(b[0] + b[1]) / 2, b[2], b[3], b[0]))

    columns: list[dict[str, Any]] = []
    for item in items:
        x0, x1 = item[0], item[1]
        for col in columns:
            overlap = min(x1, col["x1"]) - max(x0, col["x0"])
            if overlap > COLUMN_OVERLAP * min(x1 - x0, col["x1"] - col["x0"]):
                col["items"].append(item)
                col["x0"], col["x1"] = min(col["x0"], x0), max(col["x1"], x1)
                break
        else:
            columns.append({"x0": x0, "x1": x1, "items": [item]})

    return [it[6] for col in columns for it in _top_to_bottom(col["items"])]


def _top_to_bottom(items: list[tuple]) -> list[tuple]:
    """Trong 1 cột: trên → dưới; các khung SONG SONG (chú thích chữ nhỏ 2 hàng,
    cùng khoảng y) đọc phải → trái, không xen theo mép trên lệch vài pixel."""
    bands: list[dict[str, Any]] = []
    for it in sorted(items, key=lambda it: (it[2], -(it[0] + it[1]) / 2, it[3])):
        y0, y1 = it[2], it[5]
        band = bands[-1] if bands else None
        if band is not None:
            overlap = min(y1, band["y1"]) - max(y0, band["y0"])
            if overlap > SIDE_BY_SIDE_OVERLAP * min(y1 - y0, band["y1"] - band["y0"]):
                band["items"].append(it)
                band["y1"] = max(band["y1"], y1)
                continue
        bands.append({"y0": y0, "y1": y1, "items": [it]})
    return [it for band in bands for it in sorted(band["items"], key=lambda it: (-(it[0] + it[1]) / 2, it[2], it[3]))]


def boxes_from_json(path: Path) -> list[tuple[Any, str, float | None]] | None:
    data = json.loads(path.read_text(encoding="utf-8"))
    raw = data.get("result_bbox")
    if not isinstance(raw, list):
        return None
    boxes = []
    for entry in raw:
        poly, (text, score) = entry
        boxes.append((poly, text, score))
    return boxes


def load(book: dict[str, Any], stem: str, family_tree_root: Path) -> EngineResult | None:
    candidates = paddle_dir_candidates(book, family_tree_root)
    json_path = first_existing_file(candidates, f"{stem}-paddleocr.json")
    boxes = boxes_from_json(json_path) if json_path is not None else None
    if boxes:
        ordered = column_order(boxes)
        if ordered:
            return EngineResult(
                engine=ENGINE_NAME,
                lines=[text for text, _ in ordered],
                scores={text: float(score) for text, score in ordered if score is not None},
            )

    txt_path = first_existing_file(candidates, f"{stem}-paddleocr.txt")
    if txt_path is None:
        return None
    lines = [ln.strip() for ln in txt_path.read_text(encoding="utf-8").splitlines() if ln.strip()]
    if not lines:
        return None
    return EngineResult(engine=ENGINE_NAME, lines=lines, scores={})
