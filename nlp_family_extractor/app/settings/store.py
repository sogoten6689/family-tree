from __future__ import annotations

import base64
import hashlib
import os
from typing import List, Optional

from cryptography.fernet import Fernet, InvalidToken
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.settings.models import AppSetting


class SettingsStoreError(Exception):
    pass


def _fernet() -> Fernet:
    # Cùng cách lấy secret với app/hannom/credential_store.py — 1 khoá mã
    # hoá chung cho mọi config nhạy cảm lưu DB, không cần biến env riêng.
    secret = (os.getenv("SETTINGS_SECRET_KEY") or os.getenv("JWT_SECRET_KEY") or "").strip()
    if not secret:
        raise SettingsStoreError(
            "Thiếu JWT_SECRET_KEY hoặc SETTINGS_SECRET_KEY để mã hoá config lưu DB."
        )
    digest = hashlib.sha256(secret.encode("utf-8")).digest()
    return Fernet(base64.urlsafe_b64encode(digest))


def _encrypt(value: str) -> str:
    return _fernet().encrypt(value.encode("utf-8")).decode("utf-8")


def _decrypt(value: str) -> str:
    return _fernet().decrypt(value.encode("utf-8")).decode("utf-8")


def _mask(value: str) -> str:
    cleaned = value.strip()
    if len(cleaned) <= 8:
        return "*" * len(cleaned)
    return f"{cleaned[:4]}...{cleaned[-4:]}"


class SettingsStore:
    def list_all(self, db: Session) -> List[AppSetting]:
        return list(db.scalars(select(AppSetting).order_by(AppSetting.key)).all())

    def get_value(self, db: Session, key: str) -> Optional[str]:
        row = db.get(AppSetting, key)
        if row is None or not row.value_enc:
            return None
        try:
            return _decrypt(row.value_enc)
        except InvalidToken:
            return None

    def get_masked(self, db: Session, key: str) -> Optional[str]:
        value = self.get_value(db, key)
        return _mask(value) if value else None

    def set_value(self, db: Session, key: str, value: str) -> AppSetting:
        clean_key = key.strip()
        if not clean_key:
            raise SettingsStoreError("key không được rỗng")
        row = db.get(AppSetting, clean_key)
        enc = _encrypt(value)
        if row is None:
            row = AppSetting(key=clean_key, value_enc=enc)
            db.add(row)
        else:
            row.value_enc = enc
        db.commit()
        db.refresh(row)
        return row

    def delete(self, db: Session, key: str) -> bool:
        row = db.get(AppSetting, key)
        if row is None:
            return False
        db.delete(row)
        db.commit()
        return True
