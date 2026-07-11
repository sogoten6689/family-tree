from __future__ import annotations

from app.database import Base, get_engine
from app.vgp import models as _vgp_models  # noqa: F401


def ensure_vgp_schema() -> None:
    Base.metadata.create_all(bind=get_engine(), tables=[_vgp_models.VgpCrawl.__table__])


def bootstrap_vgp() -> None:
    ensure_vgp_schema()
