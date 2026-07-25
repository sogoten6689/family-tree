from __future__ import annotations

import base64
import hashlib
import os
import threading
from datetime import datetime, timezone
from typing import Any

from cryptography.fernet import Fernet, InvalidToken
from sqlalchemy.orm import Session

from app.database import database_enabled, session_scope
from app.hannom.auth import fetch_hannom_token
from app.hannom.errors import HannomApiError
from app.hannom.jwt_utils import is_token_expiring_soon, parse_jwt_expiry
from app.hannom.models import SINGLETON_ID, HannomCredential

_refresh_lock = threading.Lock()


def _mask_token(token: str) -> str:
    cleaned = token.strip()
    if cleaned.lower().startswith("bearer "):
        cleaned = cleaned[7:].strip()
    if len(cleaned) <= 12:
        return "*" * len(cleaned)
    return f"{cleaned[:8]}...{cleaned[-4:]}"


def _fernet() -> Fernet:
    secret = (os.getenv("HANNOM_SECRETS_KEY") or os.getenv("JWT_SECRET_KEY") or "").strip()
    if not secret:
        raise HannomApiError(
            "Thiếu JWT_SECRET_KEY hoặc HANNOM_SECRETS_KEY để mã hóa credential Kim Hán Nôm.",
        )
    digest = hashlib.sha256(secret.encode("utf-8")).digest()
    key = base64.urlsafe_b64encode(digest)
    return Fernet(key)


def _encrypt(value: str) -> str:
    return _fernet().encrypt(value.encode("utf-8")).decode("utf-8")


def _decrypt(value: str) -> str:
    try:
        return _fernet().decrypt(value.encode("utf-8")).decode("utf-8")
    except InvalidToken as exc:
        raise HannomApiError(
            "Không giải mã được credential Kim Hán Nôm. "
            "Kiểm tra JWT_SECRET_KEY / HANNOM_SECRETS_KEY hoặc lưu lại tài khoản.",
        ) from exc


class HannomCredentialStore:
    def get_row(self, db: Session) -> HannomCredential | None:
        return db.get(HannomCredential, SINGLETON_ID)

    def get_status(self, db: Session) -> dict[str, Any]:
        row = self.get_row(db)
        if row is None:
            return {
                "configured": False,
                "username": None,
                "has_password": False,
                "token_preview": None,
                "token_expires_at": None,
                "last_login_at": None,
                "last_error": None,
            }

        token_preview = None
        if row.token_enc:
            try:
                token_preview = _mask_token(_decrypt(row.token_enc))
            except HannomApiError:
                token_preview = "(decrypt error)"

        return {
            "configured": bool(row.password_enc),
            "username": row.username,
            "has_password": bool(row.password_enc),
            "token_preview": token_preview,
            "token_expires_at": row.token_expires_at,
            "last_login_at": row.last_login_at,
            "last_error": row.last_error,
        }

    def save_and_login(
        self,
        db: Session,
        *,
        username: str,
        password: str,
    ) -> dict[str, Any]:
        user = username.strip()
        pwd = password.strip()
        if not user or not pwd:
            raise HannomApiError("Username và password Kim Hán Nôm là bắt buộc.")

        try:
            login_result = fetch_hannom_token(username=user, password=pwd)
        except HannomApiError as exc:
            row = self.get_row(db)
            if row is None:
                row = HannomCredential(
                    id=SINGLETON_ID,
                    username=user,
                    password_enc=_encrypt(pwd),
                )
                db.add(row)
            else:
                row.username = user
                row.password_enc = _encrypt(pwd)
            row.last_error = str(exc)
            row.updated_at = datetime.now(timezone.utc)
            db.flush()
            raise

        token = str(login_result["token"])
        self._persist_login(db, user=user, password=pwd, token=token, source=str(login_result["source"]))
        return login_result

    def _persist_login(
        self,
        db: Session,
        *,
        user: str,
        password: str,
        token: str,
        source: str,
    ) -> HannomCredential:
        now = datetime.now(timezone.utc)
        row = self.get_row(db)
        if row is None:
            row = HannomCredential(id=SINGLETON_ID, username=user, password_enc=_encrypt(password))
            db.add(row)
        else:
            row.username = user
            row.password_enc = _encrypt(password)

        row.token_enc = _encrypt(token)
        row.token_expires_at = parse_jwt_expiry(token)
        row.token_source = source
        row.last_login_at = now
        row.last_error = None
        row.updated_at = now
        db.flush()
        return row

    def persist_token_from_login(
        self,
        db: Session,
        *,
        username: str,
        password: str | None,
        token: str,
        source: str,
    ) -> None:
        row = self.get_row(db)
        pwd = password
        if not pwd and row is not None:
            pwd = _decrypt(row.password_enc)
        if not pwd:
            raise HannomApiError("Không có password để lưu credential — gửi password hoặc lưu trước qua PUT.")

        self._persist_login(db, user=username.strip(), password=pwd.strip(), token=token, source=source)

    def get_valid_token(self, db: Session | None = None) -> str | None:
        if not database_enabled():
            return None

        if db is not None:
            return self._get_valid_token_with_session(db)

        with session_scope() as scoped_db:
            return self._get_valid_token_with_session(scoped_db)

    def _get_valid_token_with_session(self, db: Session) -> str | None:
        row = self.get_row(db)
        if row is None or not row.password_enc:
            return None

        if row.token_enc:
            try:
                token = _decrypt(row.token_enc)
                if not is_token_expiring_soon(token):
                    return token
            except HannomApiError:
                pass

        with _refresh_lock:
            db.refresh(row)
            if row.token_enc:
                try:
                    token = _decrypt(row.token_enc)
                    if not is_token_expiring_soon(token):
                        return token
                except HannomApiError:
                    pass

            try:
                password = _decrypt(row.password_enc)
                login_result = fetch_hannom_token(username=row.username, password=password)
            except HannomApiError as exc:
                row.last_error = str(exc)
                row.updated_at = datetime.now(timezone.utc)
                db.flush()
                return None

            token = str(login_result["token"])
            self._persist_login(
                db,
                user=row.username,
                password=password,
                token=token,
                source=str(login_result["source"]),
            )
            return token

    def force_refresh(self) -> str | None:
        with _refresh_lock:
            if not database_enabled():
                return None
            with session_scope() as db:
                row = self.get_row(db)
                if row is None or not row.password_enc:
                    return None
                try:
                    password = _decrypt(row.password_enc)
                    login_result = fetch_hannom_token(username=row.username, password=password)
                except HannomApiError as exc:
                    row.last_error = str(exc)
                    row.updated_at = datetime.now(timezone.utc)
                    return None

                token = str(login_result["token"])
                self._persist_login(
                    db,
                    user=row.username,
                    password=password,
                    token=token,
                    source=str(login_result["source"]),
                )
                return token


_credential_store = HannomCredentialStore()


def get_credential_store() -> HannomCredentialStore:
    return _credential_store
