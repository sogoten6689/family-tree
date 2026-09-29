from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.auth.dependencies import AdminUser
from app.database import database_enabled, get_db
from app.settings.schemas import SettingItem, SettingUpsertRequest
from app.settings.store import SettingsStore, SettingsStoreError

router = APIRouter(prefix="/api/admin/settings", tags=["Admin - Cấu hình"])

# Danh sách key gợi ý sẵn cho UI (không giới hạn — vẫn nhận key tuỳ ý qua PUT).
KNOWN_SETTING_KEYS = ["GOOGLE_API_KEY"]


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
