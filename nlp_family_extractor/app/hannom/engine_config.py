from __future__ import annotations

from typing import Any

# Bật/tắt engine OCR cho pipeline v2 (Admin › Cấu hình). Vẫn lưu ở setting
# HANNOM_VOTE_ENGINES (chuỗi phân tách dấu phẩy, thứ tự = ưu tiên khi vote)
# để tương thích ngược với config.get_hannom_vote_engines() và cấu hình cũ.

SETTING_KEY = "HANNOM_VOTE_ENGINES"

# Đã chốt với người dùng 2026-10-02: tối thiểu 1 engine luôn bật — pipeline
# không chạy được với 0 engine. (1–2 engine: kết quả = backbone, chỉ ≥3 engine
# mới vote per-line thật — xem app/hannom/vote.py.)
MIN_ENABLED_ENGINES = 1

ENGINE_LABELS: dict[str, str] = {
    "kimhannom": "Kim Hán Nôm Lab",
    "gemini_vision": "Gemini Vision",
}


class EngineConfigError(ValueError):
    """Cấu hình engine không hợp lệ (tên lạ, hoặc ít hơn mức tối thiểu)."""


def known_engines() -> list[str]:
    from app.hannom.engines import ENGINE_REGISTRY

    return list(ENGINE_REGISTRY)


def validate_enabled(
    names: list[str],
    current_order: list[str],
    *,
    registry: list[str] | None = None,
    min_enabled: int = MIN_ENABLED_ENGINES,
) -> list[str]:
    """Kiểm tra danh sách engine muốn bật, trả về chuỗi đã chuẩn hoá theo thứ
    tự ưu tiên: giữ thứ tự cấu hình hiện tại, engine mới bật xếp sau theo thứ
    tự registry. Raise EngineConfigError nếu có tên lạ hoặc < tối thiểu.
    Mặc định là engine OCR; engine phiên âm/dịch truyền registry riêng."""
    registry = known_engines() if registry is None else registry
    cleaned = list(dict.fromkeys(name.strip() for name in names if name.strip()))
    unknown = [name for name in cleaned if name not in registry]
    if unknown:
        raise EngineConfigError(f"Engine không tồn tại: {', '.join(unknown)}. Có sẵn: {', '.join(registry)}.")
    if len(cleaned) < min_enabled:
        raise EngineConfigError(f"Phải bật ít nhất {min_enabled} engine.")
    wanted = set(cleaned)
    ordered = [name for name in current_order if name in wanted]
    ordered += [name for name in registry if name in wanted and name not in ordered]
    return ordered


def engine_ready(name: str) -> tuple[bool, str | None]:
    """Engine có đủ cấu hình để chạy không (key/token) — chỉ để hiển thị cho
    admin, không chặn việc bật/tắt."""
    if name == "kimhannom":
        from app.hannom.client import get_effective_token
        from app.hannom.errors import HannomApiError

        try:
            get_effective_token()
            return True, None
        except HannomApiError:
            return False, "Chưa có token Kim Hán Nôm (Cấu hình Hán Nôm)."
        except Exception as error:  # DB lỗi khi đọc credential
            return False, f"Không kiểm tra được token: {error}"
    if name == "gemini_vision":
        from app.config import get_google_api_key

        return (True, None) if get_google_api_key() else (False, "Chưa có GOOGLE_API_KEY.")
    return False, "Engine chưa có cách kiểm tra cấu hình."


def describe_engines(enabled: list[str]) -> list[dict[str, Any]]:
    enabled_set = set(enabled)
    items = []
    for name in known_engines():
        ready, reason = engine_ready(name)
        items.append(
            {
                "name": name,
                "label": ENGINE_LABELS.get(name, name),
                "enabled": name in enabled_set,
                "ready": ready,
                "ready_reason": reason,
            }
        )
    return items
