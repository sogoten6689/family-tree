from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.auth.dependencies import AdminUser
from app.database import database_enabled, get_db
from app.hannom import engine_config
from app.settings.schemas import (
    OcrEngineConfig,
    OcrEngineItem,
    OcrEngineUpdateRequest,
    SettingItem,
    TextEngineConfig,
    SettingUpsertRequest,
)
from app.settings.store import SettingsStore, SettingsStoreError

router = APIRouter(prefix="/api/admin/settings", tags=["Admin - Cấu hình"])

# Danh sách key gợi ý sẵn cho UI (không giới hạn — vẫn nhận key tuỳ ý qua PUT).
KNOWN_SETTING_KEYS = [
    "GOOGLE_API_KEY",
    "LLM_PROVIDER",
    "RAMCLOUD_KEY",
    "RAMCLOUD_BASE_URL",
    "RAMCLOUD_MODEL",
    "HANNOM_PIPELINE_VERSION",
    "HANNOM_VOTE_ENGINES",
    "HANNOM_LAB_OCR_ID",
    "HANNOM_LAB_LANG_TYPE",
]


def _require_db() -> None:
    if not database_enabled():
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="MySQL chưa cấu hình — không thể lưu config vào DB.",
        )


@router.get("", response_model=list[SettingItem], summary="Danh sách config key-value đã lưu")
def list_settings(_: AdminUser, db: Session = Depends(get_db)) -> list[SettingItem]:
    _require_db()
    store = SettingsStore()
    rows = store.list_all(db)
    saved_keys = {row.key for row in rows}
    items = []
    for row in rows:
        items.append(
            SettingItem(
                key=row.key,
                masked_value=store.get_masked(db, row.key),
                configured=bool(row.value_enc),
                updated_at=row.updated_at.isoformat() if row.updated_at else None,
            )
        )
    # Gợi ý các key đã biết nhưng chưa cấu hình, để UI hiện sẵn ô nhập.
    for key in KNOWN_SETTING_KEYS:
        if key not in saved_keys:
            items.append(SettingItem(key=key, masked_value=None, configured=False, updated_at=None))
    return items


@router.put("/{key}", response_model=SettingItem, summary="Lưu/cập nhật 1 config key-value")
def upsert_setting(
    key: str,
    payload: SettingUpsertRequest,
    _: AdminUser,
    db: Session = Depends(get_db),
) -> SettingItem:
    _require_db()
    store = SettingsStore()
    try:
        row = store.set_value(db, key, payload.value)
    except SettingsStoreError as error:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(error)) from error
    return SettingItem(
        key=row.key,
        masked_value=store.get_masked(db, row.key),
        configured=True,
        updated_at=row.updated_at.isoformat() if row.updated_at else None,
    )


@router.delete("/{key}", summary="Xoá 1 config key-value")
def delete_setting(key: str, _: AdminUser, db: Session = Depends(get_db)) -> dict:
    _require_db()
    store = SettingsStore()
    deleted = store.delete(db, key)
    if not deleted:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Không tìm thấy key")
    return {"deleted": key}


# ── Bật/tắt engine OCR (pipeline v2) — giao diện có cấu trúc thay cho việc gõ
# tay chuỗi HANNOM_VOTE_ENGINES; vẫn lưu đúng key đó (tương thích ngược). ──
ocr_engines_router = APIRouter(prefix="/api/admin/ocr-engines", tags=["Admin - Cấu hình"])


def _current_engine_order(db: Session) -> list[str]:
    from app.config import get_hannom_vote_engines

    stored = SettingsStore().get_value(db, engine_config.SETTING_KEY)
    if stored:
        return [item.strip() for item in stored.split(",") if item.strip()]
    return get_hannom_vote_engines()  # mặc định khi chưa lưu


def _engine_config_response(enabled: list[str]) -> OcrEngineConfig:
    return OcrEngineConfig(
        min_enabled=engine_config.MIN_ENABLED_ENGINES,
        engines=[OcrEngineItem(**item) for item in engine_config.describe_engines(enabled)],
    )


@ocr_engines_router.get("", response_model=OcrEngineConfig, summary="Danh sách engine OCR + trạng thái bật/tắt")
def get_ocr_engines(_: AdminUser, db: Session = Depends(get_db)) -> OcrEngineConfig:
    _require_db()
    return _engine_config_response(_current_engine_order(db))


@ocr_engines_router.put("", response_model=OcrEngineConfig, summary="Lưu danh sách engine OCR được bật")
def update_ocr_engines(
    payload: OcrEngineUpdateRequest,
    _: AdminUser,
    db: Session = Depends(get_db),
) -> OcrEngineConfig:
    _require_db()
    try:
        ordered = engine_config.validate_enabled(payload.enabled, _current_engine_order(db))
    except engine_config.EngineConfigError as error:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(error)) from error
    try:
        SettingsStore().set_value(db, engine_config.SETTING_KEY, ",".join(ordered))
    except SettingsStoreError as error:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(error)) from error
    return _engine_config_response(ordered)


# ── Bật/tắt engine phiên âm/dịch nghĩa (app/hannom/text_engines.py) — engine
# do người dùng tự đăng ký trong text_engines_local.py. Bắt buộc bật ≥1 khi
# đã có engine đăng ký. ──
text_engines_router = APIRouter(prefix="/api/admin/text-engines", tags=["Admin - Cấu hình"])


def _text_engine_response(enabled: list[str]) -> TextEngineConfig:
    from app.hannom import text_engines

    return TextEngineConfig(
        min_enabled=text_engines.MIN_ENABLED_TEXT_ENGINES,
        load_error=text_engines.load_error(),
        engines=[
            OcrEngineItem(name=name, label=name, enabled=name in enabled, ready=True)
            for name in text_engines.registered_engines()
        ],
    )


@text_engines_router.get("", response_model=TextEngineConfig, summary="Engine phiên âm/dịch đã đăng ký + bật/tắt")
def get_text_engines(_: AdminUser, db: Session = Depends(get_db)) -> TextEngineConfig:
    from app.hannom import text_engines

    _require_db()
    return _text_engine_response(text_engines.enabled_engines(SettingsStore().get_value(db, text_engines.SETTING_KEY)))


@text_engines_router.put("", response_model=TextEngineConfig, summary="Lưu engine phiên âm/dịch được bật")
def update_text_engines(
    payload: OcrEngineUpdateRequest,
    _: AdminUser,
    db: Session = Depends(get_db),
) -> TextEngineConfig:
    from app.hannom import text_engines

    _require_db()
    current = text_engines.enabled_engines(SettingsStore().get_value(db, text_engines.SETTING_KEY))
    try:
        ordered = engine_config.validate_enabled(
            payload.enabled,
            current,
            registry=text_engines.registered_engines(),
            min_enabled=text_engines.MIN_ENABLED_TEXT_ENGINES,
        )
    except engine_config.EngineConfigError as error:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(error)) from error
    try:
        SettingsStore().set_value(db, text_engines.SETTING_KEY, ",".join(ordered))
    except SettingsStoreError as error:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(error)) from error
    return _text_engine_response(ordered)


# ── Số token Gemini theo loại việc (app/gemini_usage.py) — đo chi phí thật
# trước khi tối ưu. ──
gemini_usage_router = APIRouter(prefix="/api/admin/gemini-usage", tags=["Admin - Cấu hình"])


@gemini_usage_router.get("", summary="Tổng hợp số token Gemini theo loại việc")
def get_gemini_usage(_: AdminUser, days: int = 30, db: Session = Depends(get_db)) -> dict:
    from app.gemini_usage import summarize

    _require_db()
    if not 1 <= days <= 365:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="days phải từ 1 đến 365.")
    return summarize(db, days=days)
