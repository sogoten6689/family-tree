#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Adapter — OpenAI GPT đọc ẢNH ra chữ Hán (engine OCR thứ 6, 2026-10-04).

Mục đích: bộ chỉ có 3 engine (pdf-*, hxh-129, Phan gia) không bao giờ tự sửa
được chữ khi vote theo từng chữ (cần ≥3 phiếu) — thêm 1 engine độc lập.

Khoá: OPENAI_API_KEY (dạng sk-…) trong family-tree/nlp_family_extractor/.env
(KHÔNG commit) hoặc biến môi trường. Model: OPENAI_OCR_MODEL (mặc định gpt-4.1).
Gọi thẳng HTTP (requests) — không cần gói `openai`.

TỐN TIỀN: mỗi trang 1 request có ảnh. Thiếu khoá → bỏ qua (None), không gọi gì.

Khác các adapter cũ (rút kinh nghiệm hxh-129, 04/10/2026):
- Lỗi API/mạng IN RA stderr (trước đây nuốt im lặng → Google Vision hỏng cả
  lần chạy mà không ai biết).
- Kết quả không có chữ Hán (LLM trả lời kiểu "trang trống", "no text") hoặc chỉ
  là câu báo trống bằng chữ Hán ("空白页", "没有…文字") → None, không lưu như OCR.
"""
from __future__ import annotations

import base64
import os
import re
import sys
from pathlib import Path
from typing import Any

from dotenv import load_dotenv

from .base import EngineResult, first_existing_file, pages_dir_candidates
from _repo_paths import FAMILY_TREE

ENGINE_NAME = "gpt_vision"
API_URL = "https://api.openai.com/v1/chat/completions"
DEFAULT_MODEL = "gpt-4.1"
TIMEOUT_S = 90
_ENV_LOADED = False

PROMPT = (
    "Đây là ảnh chụp trang gia phả chữ Hán cổ. Chỉ trả về NGUYÊN VĂN chữ Hán "
    "đọc được trong ảnh, theo đúng thứ tự cột từ phải sang trái, mỗi cột 1 "
    "dòng. Không dịch nghĩa, không giải thích, không thêm ký tự nào ngoài "
    "nguyên văn Hán. Nếu trang không có chữ Hán đọc được thì trả về chuỗi rỗng."
)

_HAN = re.compile(r"[㐀-䶿一-鿿豈-﫿\U00020000-\U000323af]")
_NO_TEXT = re.compile(r"空白|没有.{0,12}(文字|汉字|漢字|内容)|無.{0,6}(文字|漢字)|无法(识别|提取)")


def _api_key() -> str | None:
    global _ENV_LOADED
    if not _ENV_LOADED:
        env = FAMILY_TREE / "nlp_family_extractor" / ".env"
        if env.is_file():
            load_dotenv(env)
        _ENV_LOADED = True
    return os.getenv("OPENAI_API_KEY")


def _find_image(book: dict[str, Any], stem: str, family_tree_root: Path) -> Path | None:
    candidates = pages_dir_candidates(book, family_tree_root)
    for ext in (".jpg", ".jpeg", ".png"):
        p = first_existing_file(candidates, f"{stem}{ext}")
        if p is not None:
            return p
    return None


def build_payload(image_bytes: bytes, mime: str, model: str) -> dict[str, Any]:
    data_url = f"data:{mime};base64,{base64.b64encode(image_bytes).decode('ascii')}"
    return {
        "model": model,
        "temperature": 0,
        "messages": [
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": PROMPT},
                    {"type": "image_url", "image_url": {"url": data_url, "detail": "high"}},
                ],
            }
        ],
    }


def clean_lines(text: str) -> list[str] | None:
    """Dòng OCR hợp lệ, hoặc None nếu không có chữ Hán / chỉ là câu báo trang trống."""
    lines = [ln.strip() for ln in (text or "").splitlines() if ln.strip()]
    joined = "".join(lines)
    if not _HAN.search(joined):
        return None
    if _NO_TEXT.search(joined) and len(_HAN.findall(joined)) < 80:
        return None
    return lines


def load(book: dict[str, Any], stem: str, family_tree_root: Path) -> EngineResult | None:
    key = _api_key()
    if not key:
        return None  # thiếu OPENAI_API_KEY → bỏ qua, không gọi
    img_path = _find_image(book, stem, family_tree_root)
    if img_path is None:
        return None
    import requests

    mime = "image/png" if img_path.suffix.lower() == ".png" else "image/jpeg"
    model = os.getenv("OPENAI_OCR_MODEL", DEFAULT_MODEL)
    try:
        resp = requests.post(
            API_URL,
            headers={"Authorization": f"Bearer {key}"},
            json=build_payload(img_path.read_bytes(), mime, model),
            timeout=TIMEOUT_S,
        )
        if resp.status_code != 200:
            print(f"[gpt_vision] trang {stem}: HTTP {resp.status_code} {resp.text[:200]}", file=sys.stderr)
            return None
        text = resp.json()["choices"][0]["message"]["content"] or ""
    except Exception as exc:  # noqa: BLE001 — 1 trang lỗi không chặn engine khác, nhưng phải thấy lỗi
        print(f"[gpt_vision] trang {stem}: {type(exc).__name__}: {exc}", file=sys.stderr)
        return None
    lines = clean_lines(text)
    if lines is None:
        print(f"[gpt_vision] trang {stem}: không có chữ Hán (bỏ)", file=sys.stderr)
        return None
    return EngineResult(engine=ENGINE_NAME, lines=lines, scores={})
