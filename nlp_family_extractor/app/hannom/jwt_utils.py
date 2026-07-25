from __future__ import annotations

import base64
import json
from datetime import datetime, timezone
from typing import Any


def parse_jwt_expiry(token: str) -> datetime | None:
    """Return UTC expiry from JWT ``exp`` claim without verifying signature."""
    cleaned = token.strip()
    if cleaned.lower().startswith("bearer "):
        cleaned = cleaned[7:].strip()
    parts = cleaned.split(".")
    if len(parts) < 2:
        return None

    payload_segment = parts[1]
    padding = "=" * (-len(payload_segment) % 4)
    try:
        raw = base64.urlsafe_b64decode(payload_segment + padding)
        payload: dict[str, Any] = json.loads(raw)
    except (ValueError, json.JSONDecodeError):
        return None

    exp = payload.get("exp")
    if not isinstance(exp, (int, float)):
        return None
    return datetime.fromtimestamp(float(exp), tz=timezone.utc)


def is_token_expiring_soon(token: str, *, buffer_seconds: int = 300) -> bool:
    expires_at = parse_jwt_expiry(token)
    if expires_at is None:
        return True
    now = datetime.now(timezone.utc)
    return expires_at.timestamp() <= now.timestamp() + buffer_seconds
