from __future__ import annotations

from app.database import Base, get_engine


def ensure_pipeline_schema() -> None:
    from app.pipeline import models as _pipeline_models  # noqa: F401

    Base.metadata.create_all(bind=get_engine())


def bootstrap_pipeline() -> None:
    ensure_pipeline_schema()
