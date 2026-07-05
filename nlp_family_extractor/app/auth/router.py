from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.auth.dependencies import AdminUser, CurrentUser
from app.auth.models import UserRole
from app.auth.schemas import (
    LoginRequest,
    MessageResponse,
    RegisterRequest,
    TokenResponse,
    UserListResponse,
    UserResponse,
    UserRoleUpdateRequest,
)
from app.auth.security import create_access_token, verify_password
from app.auth.user_repository import UserRepository
from app.database import database_enabled, get_db


def require_database() -> None:
    if not database_enabled():
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database chưa được cấu hình. Thiết lập biến môi trường MYSQL_*.",
        )

router = APIRouter(prefix="/api", tags=["Auth"], dependencies=[Depends(require_database)])


def _repo(db: Session = Depends(get_db)) -> UserRepository:
    return UserRepository(db)


@router.post(
    "/register",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Đăng ký tài khoản",
)
def register(payload: RegisterRequest, repo: UserRepository = Depends(_repo)) -> UserResponse:
    existing = repo.get_by_email(payload.email)
    if existing is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Email đã được sử dụng.",
        )

    user = repo.create_user(
        email=payload.email,
        password=payload.password,
        full_name=payload.full_name,
        role=UserRole.USER,
    )
    return UserResponse.model_validate(user)


@router.post("/login", response_model=TokenResponse, summary="Đăng nhập")
def login(payload: LoginRequest, repo: UserRepository = Depends(_repo)) -> TokenResponse:
    user = repo.get_by_email(payload.email)
    if user is None or not verify_password(payload.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Email hoặc mật khẩu không đúng.",
        )

    access_token = create_access_token(
        user_id=user.id,
        email=user.email,
        role=user.role.value,
    )
    return TokenResponse(
        access_token=access_token,
        user=UserResponse.model_validate(user),
    )


@router.get("/me", response_model=UserResponse, summary="Thông tin người dùng hiện tại")
def get_me(current_user: CurrentUser) -> UserResponse:
    return UserResponse.model_validate(current_user)


@router.get(
    "/users",
    response_model=UserListResponse,
    summary="Danh sách người dùng (Admin)",
)
def list_users(_: AdminUser, repo: UserRepository = Depends(_repo)) -> UserListResponse:
    users = repo.list_users()
    return UserListResponse(
        total=repo.count_users(),
        items=[UserResponse.model_validate(user) for user in users],
    )


@router.patch(
    "/users/{user_id}/role",
    response_model=UserResponse,
    summary="Cập nhật role người dùng (Admin)",
)
def update_user_role(
    user_id: int,
    payload: UserRoleUpdateRequest,
    admin: AdminUser,
    repo: UserRepository = Depends(_repo),
) -> UserResponse:
    user = repo.get_by_id(user_id)
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User không tồn tại.")

    if user.id == admin.id and payload.role != UserRole.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Không thể tự hạ quyền admin của chính mình.",
        )

    updated = repo.update_role(user, payload.role)
    return UserResponse.model_validate(updated)


@router.delete(
    "/users/{user_id}",
    response_model=MessageResponse,
    summary="Xóa người dùng (Admin)",
)
def delete_user(
    user_id: int,
    admin: AdminUser,
    repo: UserRepository = Depends(_repo),
) -> MessageResponse:
    user = repo.get_by_id(user_id)
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User không tồn tại.")

    if user.id == admin.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Không thể xóa tài khoản admin đang đăng nhập.",
        )

    repo.delete_user(user)
    return MessageResponse(message="Đã xóa user thành công.")
