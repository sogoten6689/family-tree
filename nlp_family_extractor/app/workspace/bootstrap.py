from __future__ import annotations

from app.database import Base, database_enabled, get_engine


def ensure_workspace_schema() -> None:
    if not database_enabled():
        return
    engine = get_engine()
    if engine is None:
        return
    from app.workspace import models  # noqa: F401

    Base.metadata.create_all(bind=engine, tables=[models.UserScan.__table__])


def bootstrap_workspace() -> None:
    if not database_enabled():
        return
    ensure_workspace_schema()
