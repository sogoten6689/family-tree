#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Adapter — DeepSeek Vision OCR (đọc ẢNH trực tiếp qua model đa phương thức).

XÁC NHẬN 2026-09-09: `DEEPSEEK_API_KEY` tạo trực tiếp bởi user (đăng nhập tài
khoản DeepSeek của user, Claude không được phép tự đăng nhập) tại
https://platform.deepseek.com/api_keys, key tên "hannom-ocr", lưu trong
`.env` (KHÔNG commit — xem .gitignore) ở gốc repo này.

Model dùng: `deepseek-v4-flash-vision-exp` (model đa phương thức mới nhất trên
DeepSeek API tại thời điểm viết, endpoint OpenAI-compatible
`https://api.deepseek.com/chat/completions`, ảnh gửi dạng base64 data URL
trong content block `image_url`).

LƯU Ý CHI PHÍ: balance tài khoản DeepSeek của user tại thời điểm tạo key là
$0.00 (chưa top-up) — mỗi lần gọi tốn quota/tiền thật, cần user tự top-up
trước khi chạy hàng loạt (Claude không được phép nạp tiền thay).
"""
from __future__ import annotations

import base64
import os
from pathlib import Path
from typing import Any

from dotenv import load_dotenv
import requests

from .base import EngineResult, pages_dir_candidates, first_existing_file

ENGINE_NAME = "deepseek"
_ENV_LOADED = False

API_URL = "https://api.deepseek.com/chat/completions"
MODEL = "deepseek-v4-flash-vision-exp"

PROMPT = (
    "Đây là ảnh chụp trang gia phả chữ Hán cổ. Chỉ trả về NGUYÊN VĂN chữ Hán "
    "đọc được trong ảnh, theo đúng thứ tự cột từ phải sang trái, mỗi cột 1 "
    "dòng. Không dịch nghĩa, không giải thích, không thêm ký tự nào ngoài "
    "nguyên văn Hán."
)


def _ensure_key() -> str | None:
    global _ENV_LOADED
    if not _ENV_LOADED:
        repo_env = Path(__file__).resolve().parents[2] / ".env"
        if repo_env.is_file():
            load_dotenv(repo_env)
        _ENV_LOADED = True
    return os.getenv("DEEPSEEK_API_KEY")


def _find_image(book: dict[str, Any], stem: str, family_tree_root: Path) -> Path | None:
    candidates = pages_dir_candidates(book, family_tree_root)
    for ext in (".jpg", ".jpeg", ".png"):
        p = first_existing_file(candidates, f"{stem}{ext}")
        if p is not None:
            return p
    return None


def load(book: dict[str, Any], stem: str, family_tree_root: Path) -> EngineResult | None:
    key = _ensure_key()
    if not key:
        return None  # thiếu DEEPSEEK_API_KEY -> bỏ qua, không lỗi

    img_path = _find_image(book, stem, family_tree_root)
    if img_path is None:
        return None

    try:
        b64 = base64.b64encode(img_path.read_bytes()).decode("ascii")
        resp = requests.post(
            API_URL,
            headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
            json={
                "model": MODEL,
                "messages": [
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": PROMPT},
                            {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{b64}"}},
                        ],
                    }
                ],
            },
            timeout=60,
        )
        resp.raise_for_status()
        text = resp.json()["choices"][0]["message"]["content"].strip()
    except Exception:
        return None  # lỗi API (quota/mạng/...) -> bỏ qua trang này, không chặn engine khác

    lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
    if not lines:
        return None
    return EngineResult(engine=ENGINE_NAME, lines=lines, scores={})
