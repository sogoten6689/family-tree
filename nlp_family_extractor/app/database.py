from __future__ import annotations

import os
from contextlib import contextmanager
from typing import Generator, Optional

from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker


class Base(DeclarativeBase):
    pass


_engine: Optional[Engine] = None
_SessionLocal: Optional[sessionmaker[Session]] = None
_init_error: Optional[str] = None


def _build_database_url() -> Optional[str]:
    mysql_host = os.getenv("MYSQL_HOST")
    mysql_port = os.getenv("MYSQL_PORT", "3306")
    mysql_db = os.getenv("MYSQL_DATABASE", "family_tree")
    mysql_user = os.getenv("MYSQL_USER")
    mysql_password = os.getenv("MYSQL_PASSWORD")

    if not mysql_host or not mysql_user or not mysql_password:
        return None

    return (
        f"mysql+pymysql://{mysql_user}:{mysql_password}@{mysql_host}:{mysql_port}/{mysql_db}"
        "?charset=utf8mb4"
    )


def init_database() -> None:
    global _engine, _SessionLocal, _init_error

    database_url = _build_database_url()
    if not database_url:
        _init_error = "MySQL env vars are missing (MYSQL_HOST, MYSQL_USER, MYSQL_PASSWORD)."
        return

    try:
        _engine = create_engine(database_url, pool_pre_ping=True, future=True)
        _SessionLocal = sessionmaker(bind=_engine, autoflush=False, autocommit=False, future=True)
        _init_error = None
    except Exception as exc:  # pragma: no cover
        _engine = None
        _SessionLocal = None
        _init_error = str(exc)


def database_enabled() -> bool:
    return _engine is not None and _SessionLocal is not None


def database_init_error() -> Optional[str]:
    return _init_error


def get_engine() -> Engine:
    if _engine is None:
        raise RuntimeError(_init_error or "Database is not initialized.")
    return _engine


def get_db() -> Generator[Session, None, None]:
    if _SessionLocal is None:
        raise RuntimeError(_init_error or "Database is not initialized.")

    db = _SessionLocal()
    try:
        yield db
    finally:
        db.close()


def get_optional_db() -> Generator[Session | None, None, None]:
    if _SessionLocal is None:
        yield None
        return
    db = _SessionLocal()
    try:
        yield db
    finally:
        db.close()


@contextmanager
def session_scope() -> Generator[Session, None, None]:
    if _SessionLocal is None:
        raise RuntimeError(_init_error or "Database is not initialized.")

    db = _SessionLocal()
    try:
        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()
