from __future__ import annotations

from sqlalchemy import text

from app.database import Base, database_enabled, get_engine


def ensure_workspace_schema() -> None:
    if not database_enabled():
        return
    engine = get_engine()
    if engine is None:
        return
    from app.workspace import models  # noqa: F401

    Base.metadata.create_all(bind=engine, tables=[models.UserScan.__table__])
    _migrate_user_scans_columns(engine)


def _migrate_user_scans_columns(engine) -> None:
    with engine.begin() as conn:
        exists = conn.execute(
            text(
                "SELECT COUNT(*) AS cnt FROM information_schema.COLUMNS "
                "WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'user_scans' "
                "AND COLUMN_NAME = 'source_file_key'"
            )
        ).scalar()
        if not exists:
            conn.execute(text("ALTER TABLE user_scans ADD COLUMN source_file_key VARCHAR(512) NULL"))


def bootstrap_workspace() -> None:
    if not database_enabled():
        return
    ensure_workspace_schema()
