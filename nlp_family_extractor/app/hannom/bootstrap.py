from __future__ import annotations

from app.database import get_engine
from app.hannom.models import HannomCredential


def bootstrap_hannom() -> None:
    HannomCredential.__table__.create(bind=get_engine(), checkfirst=True)
