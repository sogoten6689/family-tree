from __future__ import annotations

from typing import List, Optional

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.auth.models import User, UserRole
from app.auth.security import hash_password


class UserRepository:
    def __init__(self, db: Session) -> None:
        self._db = db

    def get_by_id(self, user_id: int) -> Optional[User]:
        return self._db.get(User, user_id)

    def get_by_email(self, email: str) -> Optional[User]:
        stmt = select(User).where(func.lower(User.email) == email.lower())
        return self._db.scalar(stmt)

    def list_users(self) -> List[User]:
        stmt = select(User).order_by(User.created_at.desc())
        return list(self._db.scalars(stmt).all())

    def count_users(self) -> int:
        stmt = select(func.count()).select_from(User)
        return int(self._db.scalar(stmt) or 0)

    def create_user(
        self,
        *,
        email: str,
        password: str,
        full_name: str,
        role: UserRole = UserRole.USER,
    ) -> User:
        user = User(
            email=email.lower(),
            password_hash=hash_password(password),
            full_name=full_name.strip(),
            role=role,
        )
        self._db.add(user)
        self._db.commit()
        self._db.refresh(user)
        return user

    def update_role(self, user: User, role: UserRole) -> User:
        user.role = role
        self._db.add(user)
        self._db.commit()
        self._db.refresh(user)
        return user

    def update_profile(
        self,
        user: User,
        *,
        full_name: Optional[str] = None,
        password: Optional[str] = None,
    ) -> User:
        if full_name is not None:
            user.full_name = full_name.strip()
        if password is not None:
            user.password_hash = hash_password(password)
        self._db.add(user)
        self._db.commit()
        self._db.refresh(user)
        return user

    def delete_user(self, user: User) -> None:
        self._db.delete(user)
        self._db.commit()
