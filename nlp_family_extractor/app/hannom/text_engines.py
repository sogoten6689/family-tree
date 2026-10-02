from __future__ import annotations

import importlib
import logging
import re
import traceback
from typing import Any, Callable

# Khe cắm engine phiên âm + dịch nghĩa (cách B, chốt 2026-10-02). Engine là
# 1 hàm `(hannom_text, *, page_number) -> [{"cn", "sv", "vi"}, ...]` — cùng
# định dạng cổng nhập file (app/workspace/llm_import.py), nên kết quả đi qua
# đúng đường kiểm tra + tạo version. Adapter cụ thể do người dùng tự viết ở
# app/hannom/text_engines_local.py (nạp nếu tồn tại) — module này không gọi
# dịch vụ ngoài nào.

logger = logging.getLogger(__name__)

TextEngine = Callable[..., list[dict[str, Any]]]

SETTING_KEY = "HANNOM_TEXT_ENGINES"
# Đã chốt: bắt buộc bật ≥1 engine (khi đã có engine được đăng ký).
MIN_ENABLED_TEXT_ENGINES = 1
NAME_PATTERN = re.compile(r"^[a-z0-9][a-z0-9_-]{0,49}$")
LOCAL_MODULE = "app.hannom.text_engines_local"

TEXT_ENGINE_REGISTRY: dict[str, TextEngine] = {}
_load_error: str | None = None


def register_text_engine(name: str, fn: TextEngine) -> None:
    if not NAME_PATTERN.match(name):
        raise ValueError(f"Tên engine '{name}' không hợp lệ (chữ thường/số/-/_, ≤50 ký tự).")
    if not callable(fn):
        raise TypeError(f"Engine '{name}' phải là hàm.")
    TEXT_ENGINE_REGISTRY[name] = fn


def load_local_engines() -> str | None:
    """Nạp adapter người dùng. Thiếu file = bình thường; file lỗi thì ghi lại
    lỗi (hiện ở trang Cấu hình) nhưng không làm sập server."""
    global _load_error
    _load_error = None
    try:
        importlib.import_module(LOCAL_MODULE)
    except ModuleNotFoundError as error:
        if error.name != LOCAL_MODULE:
            _load_error = f"{LOCAL_MODULE}: thiếu thư viện '{error.name}'"
    except Exception:
        _load_error = f"{LOCAL_MODULE} lỗi khi nạp:\n{traceback.format_exc(limit=3)}"
    if _load_error:
        logger.error(_load_error)
    return _load_error


def load_error() -> str | None:
    return _load_error


def registered_engines() -> list[str]:
    return list(TEXT_ENGINE_REGISTRY)


def enabled_engines(stored: str | None) -> list[str]:
    """Engine đang bật = setting đã lưu (lọc tên còn đăng ký); chưa lưu thì
    mặc định bật tất cả engine đã đăng ký."""
    registry = registered_engines()
    if stored is None:
        return registry
    return [name for name in (item.strip() for item in stored.split(",")) if name in registry]
