"""Firecrawl client wrapper."""

from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv
from firecrawl import Firecrawl

PACKAGE_DIR = Path(__file__).resolve().parent


def load_env() -> None:
    env_file = PACKAGE_DIR / ".env"
    if env_file.is_file():
        load_dotenv(env_file)
    else:
        load_dotenv()


def get_client() -> Firecrawl:
    load_env()
    api_key = os.getenv("FIRECRAWL_API_KEY", "").strip()
    if not api_key:
        raise ValueError("FIRECRAWL_API_KEY is required — copy source_discovery/.env.example → .env")
    return Firecrawl(api_key=api_key)


def map_limit() -> int:
    load_env()
    raw = os.getenv("FIRECRAWL_MAX_MAP_LIMIT", "5000").strip()
    return int(raw) if raw else 5000
