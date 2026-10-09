from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

# Load .env from package root (nlp_family_extractor/) when running from repo root or this folder.
_env_path = Path(__file__).resolve().parent.parent / ".env"
load_dotenv(_env_path)
load_dotenv()

GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
GEMINI_MODEL_NAME = os.getenv("GEMINI_MODEL_NAME", "models/gemini-2.5-flash")


def get_google_api_key() -> str | None:
    """Đọc GOOGLE_API_KEY runtime — ưu tiên config lưu DB (menu Admin ›
    Developer › Cấu hình, xem app/settings/), fallback biến môi trường tĩnh
    ở trên. Đọc DB mỗi lần gọi (không cache) để admin đổi key qua UI có hiệu
    lực ngay, không cần restart server."""
    try:
        from app.database import database_enabled, session_scope

        if database_enabled():
            from app.settings.store import SettingsStore

            with session_scope() as db:
                value = SettingsStore().get_value(db, "GOOGLE_API_KEY")
                if value:
                    return value
    except Exception:
        pass
    return GOOGLE_API_KEY


def get_llm_provider() -> str:
    """Nhà cung cấp LLM cho mọi lời gọi "Gemini" trong app: "google" (mặc định,
    SDK google-genai + GOOGLE_API_KEY) hoặc "ramcloud" (API kiểu OpenAI của lab,
    RAMCLOUD_KEY). Chọn qua setting LLM_PROVIDER (Admin › Developer › Cấu hình)
    hoặc biến môi trường cùng tên; giá trị lạ → "google"."""
    value = (_get_setting("LLM_PROVIDER") or os.getenv("LLM_PROVIDER") or "google").strip().lower()
    return value if value in {"google", "ramcloud"} else "google"


def get_ramcloud_key() -> str | None:
    return _get_setting("RAMCLOUD_KEY") or os.getenv("RAMCLOUD_KEY") or None


def get_ramcloud_base_url() -> str:
    return (_get_setting("RAMCLOUD_BASE_URL") or os.getenv("RAMCLOUD_BASE_URL") or "https://ramclouds.me/v1").rstrip("/")


def get_ramcloud_model() -> str:
    return _get_setting("RAMCLOUD_MODEL") or os.getenv("RAMCLOUD_MODEL") or "gemini-3.8-flash"


def get_llm_api_key() -> str | None:
    """Khoá của nhà cung cấp LLM đang chọn — dùng để kiểm tra "đã cấu hình chưa"
    trước khi gọi (thay cho get_google_api_key ở các chỗ không riêng Google)."""
    if get_llm_provider() == "ramcloud":
        return get_ramcloud_key()
    return get_google_api_key()


def _get_setting(key: str) -> str | None:
    """Đọc 1 setting runtime từ DB (Admin › Developer › Cấu hình), không
    cache — cùng pattern get_google_api_key(). Trả None nếu DB tắt/lỗi/chưa
    set, để caller tự quyết định fallback."""
    try:
        from app.database import database_enabled, session_scope

        if database_enabled():
            from app.settings.store import SettingsStore

            with session_scope() as db:
                value = SettingsStore().get_value(db, key)
                if value:
                    return value
    except Exception:
        pass
    return None


def get_hannom_pipeline_version() -> str:
    """"v1" (OCR → phiên âm, mặc định) hoặc "v2" (OCR nhiều engine → vote →
    phiên âm → dịch nghĩa) — chọn qua setting HANNOM_PIPELINE_VERSION."""
    value = _get_setting("HANNOM_PIPELINE_VERSION")
    return value.strip().lower() if value else "v1"


def get_hannom_vote_engines() -> list[str]:
    """Danh sách engine dùng để vote khi pipeline v2 — setting
    HANNOM_VOTE_ENGINES, phân tách dấu phẩy. Mặc định 2 engine đã triển khai:
    kimhannom + gemini_vision (xem app/hannom/engines.py:ENGINE_REGISTRY)."""
    value = _get_setting("HANNOM_VOTE_ENGINES")
    raw = value if value else "kimhannom,gemini_vision"
    return [item.strip() for item in raw.split(",") if item.strip()]


def get_hannom_lab_ocr_id() -> int | None:
    """Giá trị mặc định ocr_id cho pipeline live khi caller không truyền rõ
    — setting HANNOM_LAB_OCR_ID, fallback env var HANNOM_OCR_ID cũ (đọc trực
    tiếp trong app/hannom/client.py nếu cả 2 đều không set)."""
    value = _get_setting("HANNOM_LAB_OCR_ID")
    if value is None:
        return None
    try:
        return int(value)
    except ValueError:
        return None


def get_hannom_lab_lang_type() -> int | None:
    """Giá trị mặc định lang_type cho pipeline live — setting
    HANNOM_LAB_LANG_TYPE, cùng cơ chế fallback như get_hannom_lab_ocr_id()."""
    value = _get_setting("HANNOM_LAB_LANG_TYPE")
    if value is None:
        return None
    try:
        return int(value)
    except ValueError:
        return None
