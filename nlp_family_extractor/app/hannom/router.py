from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.auth.dependencies import AdminUser
from app.database import database_enabled, get_db
from app.hannom.auth import fetch_hannom_token, get_token_status, resolve_hannom_credentials
from app.hannom.credential_store import get_credential_store
from app.hannom.errors import HannomApiError
from app.hannom.schemas import (
    HannomCredentialsStatusResponse,
    HannomCredentialsUpdateRequest,
    HannomFetchTokenRequest,
    HannomFetchTokenResponse,
    HannomTokenStatusResponse,
)

router = APIRouter(prefix="/api/developer/hannom", tags=["Developer - Kim Hán Nôm"])


def _require_db() -> None:
    if not database_enabled():
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="MySQL chưa cấu hình — không thể lưu credential Kim Hán Nôm.",
        )


def _raise_hannom_error(error: HannomApiError) -> None:
    raise HTTPException(
        status_code=status.HTTP_502_BAD_GATEWAY,
        detail={
            "message": str(error),
            "api_code": error.api_code,
            "upstream_status": error.status_code,
        },
    ) from error


def _serialize_credentials_status(raw: dict) -> HannomCredentialsStatusResponse:
    expires = raw.get("token_expires_at")
    last_login = raw.get("last_login_at")
    return HannomCredentialsStatusResponse(
        configured=bool(raw.get("configured")),
        username=raw.get("username"),
        has_password=bool(raw.get("has_password")),
        token_preview=raw.get("token_preview"),
        token_expires_at=expires.isoformat() if expires else None,
        last_login_at=last_login.isoformat() if last_login else None,
        last_error=raw.get("last_error"),
    )


@router.get("/token-status", response_model=HannomTokenStatusResponse, summary="Trạng thái token OCR")
def hannom_token_status(_: AdminUser) -> HannomTokenStatusResponse:
    return HannomTokenStatusResponse(**get_token_status())


@router.get(
    "/credentials",
    response_model=HannomCredentialsStatusResponse,
    summary="Trạng thái credential Kim Hán Nôm (DB)",
)
def hannom_credentials_status(_: AdminUser, db: Session = Depends(get_db)) -> HannomCredentialsStatusResponse:
    _require_db()
    raw = get_credential_store().get_status(db)
    return _serialize_credentials_status(raw)


@router.put(
    "/credentials",
    response_model=HannomCredentialsStatusResponse,
    summary="Lưu username/password → login → lưu token (DB, mã hóa)",
)
def hannom_save_credentials(
    req: HannomCredentialsUpdateRequest,
    _: AdminUser,
    db: Session = Depends(get_db),
) -> HannomCredentialsStatusResponse:
    _require_db()
    try:
        get_credential_store().save_and_login(
            db,
            username=req.username,
            password=req.password,
        )
        db.commit()
    except HannomApiError as error:
        db.commit()
        _raise_hannom_error(error)

    raw = get_credential_store().get_status(db)
    return _serialize_credentials_status(raw)


@router.post(
    "/fetch-token",
    response_model=HannomFetchTokenResponse,
    summary="Đăng nhập Kim Hán Nôm và lấy Bearer token",
)
def hannom_fetch_token(
    req: HannomFetchTokenRequest,
    _: AdminUser,
    db: Session = Depends(get_db),
) -> HannomFetchTokenResponse:
    username, password = resolve_hannom_credentials(
        email=req.email,
        username=req.username,
        password=req.password,
    )
    if not username or not password:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cần email/tên đăng nhập và mật khẩu (form hoặc HANNOM_EMAIL/HANNOM_PASSWORD trên server).",
        )

    try:
        result = fetch_hannom_token(username=username, password=password)
    except HannomApiError as error:
        _raise_hannom_error(error)

    if database_enabled():
        try:
            get_credential_store().persist_token_from_login(
                db,
                username=str(result["username"]),
                password=password,
                token=str(result["token"]),
                source=str(result["source"]),
            )
            db.commit()
        except HannomApiError:
            db.rollback()

    token = str(result["token"])
    preview = token if len(token) <= 12 else f"{token[:8]}...{token[-4:]}"
    return HannomFetchTokenResponse(
        token=token,
        token_preview=preview,
        token_length=len(token),
        source=str(result["source"]),
        login_path=str(result["login_path"]),
        username=str(result["username"]),
        message=(
            "Đã lấy token thành công. Token đã áp dụng runtime"
            + (" và lưu DB (mã hóa)." if database_enabled() else ". Bật MySQL để lưu lâu dài.")
        ),
    )
