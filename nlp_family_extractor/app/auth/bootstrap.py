from __future__ import annotations

import os

from app.auth.models import UserRole
from app.auth.user_repository import UserRepository
from app.database import Base, get_engine, session_scope


def ensure_auth_schema() -> None:
    Base.metadata.create_all(bind=get_engine())


def seed_default_admin() -> None:
    admin_email = os.getenv("ADMIN_EMAIL", "admin@giapha.local").lower()
    admin_password = os.getenv("ADMIN_PASSWORD", "Admin@123456")
    admin_name = os.getenv("ADMIN_FULL_NAME", "System Admin")

    with session_scope() as db:
        repo = UserRepository(db)
        existing = repo.get_by_email(admin_email)
        if existing is not None:
            return

        repo.create_user(
            email=admin_email,
            password=admin_password,
            full_name=admin_name,
            role=UserRole.ADMIN,
        )


def bootstrap_auth() -> None:
    ensure_auth_schema()
    seed_default_admin()
