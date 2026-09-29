#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Adapter — Google Cloud Vision OCR (DOCUMENT_TEXT_DETECTION trên ảnh gốc).

XÁC NHẬN 2026-09-09: service account `hannom-ocr-vision` tạo trong Google Cloud
project "devfest" (project_id gen-lang-client-0336418096, project của user tại
HCMUS — KHÔNG dùng project "Univini"/vn-connections đã tạo nhầm trước đó), role
`roles/serviceusage.serviceUsageConsumer` (tối thiểu, đủ để gọi API đã bật,
không cấp quyền thừa lên tài nguyên khác trong project). Cloud Vision API đã
bật sẵn cho project này trước khi tạo service account. Key JSON tải về lưu tại
`secrets/google_vision_sa.json` (KHÔNG commit — xem .gitignore), trỏ qua biến
môi trường GOOGLE_APPLICATION_CREDENTIALS.

Khác GOOGLE_API_KEY (Gemini/AI Studio, dùng cho gemini.py + dịch nghĩa L3 bên
family-tree) — đây là credential Cloud Vision riêng, 2 loại không dùng thay
nhau được.
"""
from __future__ import annotations

import os
from pathlib import Path
from typing import Any

from .base import EngineResult, pages_dir_candidates, first_existing_file, call_with_timeout

ENGINE_NAME = "google_vision"
_ENV_CHECKED = False
_CLIENT = None

_KEY_PATH = Path(__file__).resolve().parents[2] / "secrets" / "google_vision_sa.json"


def _ensure_client():
    global _ENV_CHECKED, _CLIENT
    if not _ENV_CHECKED:
        _ENV_CHECKED = True
        if _KEY_PATH.is_file():
            os.environ.setdefault("GOOGLE_APPLICATION_CREDENTIALS", str(_KEY_PATH))
        if os.getenv("GOOGLE_APPLICATION_CREDENTIALS"):
            try:
                from google.cloud import vision
                _CLIENT = vision.ImageAnnotatorClient()
            except Exception:
                _CLIENT = None
    return _CLIENT


def _find_image(book: dict[str, Any], stem: str, family_tree_root: Path) -> Path | None:
    candidates = pages_dir_candidates(book, family_tree_root)
    for ext in (".jpg", ".jpeg", ".png"):
        p = first_existing_file(candidates, f"{stem}{ext}")
        if p is not None:
            return p
    return None


def load(book: dict[str, Any], stem: str, family_tree_root: Path) -> EngineResult | None:
    client = _ensure_client()
    if client is None:
        return None  # thiếu credential -> bỏ qua, không lỗi

    img_path = _find_image(book, stem, family_tree_root)
    if img_path is None:
        return None

    try:
        from google.cloud import vision
        content = img_path.read_bytes()
        image = vision.Image(content=content)
        resp = call_with_timeout(
            client.document_text_detection,
            image=image,
            image_context={"language_hints": ["zh", "zh-Hant"]},
            timeout_s=90.0,
        )
        if resp.error.message:
            return None
        text = resp.full_text_annotation.text if resp.full_text_annotation else ""
    except Exception:
        return None  # lỗi API (quota/mạng/credential hết hạn/...) -> bỏ qua trang này

    lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
    if not lines:
        return None
    return EngineResult(engine=ENGINE_NAME, lines=lines, scores={})
