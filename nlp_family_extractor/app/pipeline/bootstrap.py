from __future__ import annotations

from sqlalchemy import inspect, text

from app.database import Base, get_engine


def _ensure_pipeline_columns() -> None:
    engine = get_engine()
    inspector = inspect(engine)
    if "genealogy_pipeline_steps" not in inspector.get_table_names():
        return

    existing = {column["name"] for column in inspector.get_columns("genealogy_pipeline_steps")}
    migrations = [
        (
            "manual_override",
            "ALTER TABLE genealogy_pipeline_steps "
            "ADD COLUMN manual_override TINYINT(1) NOT NULL DEFAULT 0",
        ),
        (
            "admin_note",
            "ALTER TABLE genealogy_pipeline_steps ADD COLUMN admin_note TEXT NULL",
        ),
    ]

    with engine.begin() as connection:
        for column_name, ddl in migrations:
            if column_name not in existing:
                connection.execute(text(ddl))


def ensure_pipeline_schema() -> None:
    from app.pipeline import models as _pipeline_models  # noqa: F401

    Base.metadata.create_all(bind=get_engine())
    _ensure_pipeline_columns()


def bootstrap_pipeline() -> None:
    ensure_pipeline_schema()
