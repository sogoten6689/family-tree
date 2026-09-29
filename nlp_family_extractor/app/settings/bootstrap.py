from __future__ import annotations

from app.database import Base, database_enabled, get_engine


def ensure_settings_schema() -> None:
    if not database_enabled():
        return
    engine = get_engine()
    if engine is None:
        return
    from app.settings import models  # noqa: F401

    Base.metadata.create_all(bind=engine, tables=[models.AppSetting.__table__])


def bootstrap_settings() -> None:
    if not database_enabled():
        return
    ensure_settings_schema()
