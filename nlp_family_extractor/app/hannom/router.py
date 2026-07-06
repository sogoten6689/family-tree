from fastapi import APIRouter, HTTPException, status

from app.auth.dependencies import AdminUser
from app.hannom.auth import fetch_hannom_token, get_token_status, resolve_hannom_credentials
from app.hannom.errors import HannomApiError
from app.hannom.schemas import (
    HannomFetchTokenRequest,
    HannomFetchTokenResponse,
    HannomTokenStatusResponse,
)

router = APIRouter(prefix="/api/developer/hannom", tags=["Developer - Kim Hán Nôm"])


def _raise_hannom_error(error: HannomApiError) -> None:
    raise HTTPException(
        status_code=status.HTTP_502_BAD_GATEWAY,
        detail={
            "message": str(error),
            "api_code": error.api_code,
            "upstream_status": error.status_code,
        },
    ) from error


@router.get("/token-status", response_model=HannomTokenStatusResponse, summary="Trạng thái token OCR")
def hannom_token_status(_: AdminUser) -> HannomTokenStatusResponse:
    return HannomTokenStatusResponse(**get_token_status())


@router.post(
    "/fetch-token",
    response_model=HannomFetchTokenResponse,
    summary="Đăng nhập Kim Hán Nôm và lấy Bearer token",
)
def hannom_fetch_token(req: HannomFetchTokenRequest, _: AdminUser) -> HannomFetchTokenResponse:
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
            "Đã lấy token thành công. Token đã được áp dụng runtime cho backend hiện tại. "
            "Để giữ sau restart, cập nhật HANNOM_API_TOKEN trên VPS."
        ),
    )
