#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Adapter — Gemini Vision OCR (đọc ẢNH trực tiếp ra chữ Hán qua GOOGLE_API_KEY).

XÁC NHẬN HOẠT ĐỘNG 2026-09-09: test thật trên gpc-dang-1928 trang 1 (ảnh
data/00_raw/du_lieu_han_nom_moi/gia_pha_chi/1.jpg) bằng đúng GOOGLE_API_KEY đã
có sẵn trong family-tree/nlp_family_extractor/.env — Gemini đọc được, có chỗ
CHÍNH XÁC HƠN cả Lab lẫn Paddle (vd. "元龜" khớp đúng thành ngữ cổ điển "vi
nguyên quy" mà cả 2 engine kia đọc nhầm thành 元𬺞/元菴). Không có chỗ nào 1
engine luôn đúng — đây chính là lý do cần vote nhiều nguồn.

Phân biệt rõ với vai trò Gemini khác trong family-tree (L3 dịch nghĩa văn bản
đã có, xem dich_qwen.py) — đây là vai trò OCR (L1), đọc ảnh trực tiếp.

LƯU Ý CHI PHÍ: mỗi lần gọi tốn 1 request API thật (không đọc file cache như
paddle_v6/kim_hannom_lab) — cân nhắc số trang trước khi chạy hàng loạt (xem
--sleep trong vote_ocr.py nếu cần, và kiểm tra quota GOOGLE_API_KEY trước khi
chạy toàn bộ Track 1).
"""
from __future__ import annotations

import os
from pathlib import Path
from typing import Any

from dotenv import load_dotenv

from .base import EngineResult, pages_dir_candidates, first_existing_file, call_with_timeout
from _repo_paths import FAMILY_TREE

ENGINE_NAME = "gemini"
_ENV_LOADED = False
_CLIENT = None
_MODEL = None

PROMPT = (
    "Đây là ảnh chụp trang gia phả chữ Hán cổ. Chỉ trả về NGUYÊN VĂN chữ Hán "
    "đọc được trong ảnh, theo đúng thứ tự cột từ phải sang trái, mỗi cột 1 "
    "dòng. Không dịch nghĩa, không giải thích, không thêm ký tự nào ngoài "
    "nguyên văn Hán."
)


def _ensure_client():
    global _ENV_LOADED, _CLIENT, _MODEL
    if not _ENV_LOADED:
        family_tree_env = FAMILY_TREE / "nlp_family_extractor" / ".env"
        if family_tree_env.is_file():
            load_dotenv(family_tree_env)
        _ENV_LOADED = True
    if _CLIENT is None:
        key = os.getenv("GOOGLE_API_KEY")
        if not key:
            return None, None
        from google import genai
        _MODEL = os.getenv("GEMINI_MODEL_NAME", "models/gemini-2.5-flash")
        _CLIENT = genai.Client(api_key=key)
    return _CLIENT, _MODEL


def _find_image(book: dict[str, Any], stem: str, family_tree_root: Path) -> Path | None:
    candidates = pages_dir_candidates(book, family_tree_root)
    for ext in (".jpg", ".jpeg", ".png"):
        p = first_existing_file(candidates, f"{stem}{ext}")
        if p is not None:
            return p
    return None


def load(book: dict[str, Any], stem: str, family_tree_root: Path) -> EngineResult | None:
    client, model = _ensure_client()
    if client is None:
        return None  # thiếu GOOGLE_API_KEY -> bỏ qua, không lỗi

    img_path = _find_image(book, stem, family_tree_root)
    if img_path is None:
        return None

    try:
        from google.genai import types
        img_bytes = img_path.read_bytes()
        resp = call_with_timeout(
            client.models.generate_content,
            model=model,
            contents=[types.Part.from_bytes(data=img_bytes, mime_type="image/jpeg"), PROMPT],
            timeout_s=90.0,
        )
        text = (resp.text or "").strip()
    except Exception:
        return None  # lỗi API (quota/mạng/treo quá 90s/...) -> bỏ qua trang này, không chặn engine khác

    lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
    if not lines:
        return None
    return EngineResult(engine=ENGINE_NAME, lines=lines, scores={})
