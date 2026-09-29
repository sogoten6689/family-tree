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
