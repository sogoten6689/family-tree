from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

# Load .env from package root (nlp_family_extractor/) when running from repo root or this folder.
_env_path = Path(__file__).resolve().parent.parent / ".env"
load_dotenv(_env_path)
load_dotenv()

GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
GEMINI_MODEL_NAME = os.getenv("GEMINI_MODEL_NAME", "models/gemini-2.5-flash")
