"""Vote OCR theo từng chữ — NẠP THẲNG bản chính ở backend:
nlp_family_extractor/app/hannom/vote_char.py (nguồn duy nhất của thuật toán, có
test trong CI). Không import qua package `app` vì app/hannom/__init__.py kéo
theo pipeline/httpx; file vote_char.py chỉ cần rapidfuzz.

Giữ tên module này để các script research cũ (compare_char_vote.py, test)
không phải đổi import.
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

_SOURCE = Path(__file__).resolve().parents[3] / "nlp_family_extractor" / "app" / "hannom" / "vote_char.py"
_NAME = "family_tree_vote_char"

if _NAME in sys.modules:
    _module = sys.modules[_NAME]
else:
    _spec = importlib.util.spec_from_file_location(_NAME, _SOURCE)
    if _spec is None or _spec.loader is None:
        raise ImportError(f"Không nạp được {_SOURCE}")
    _module = importlib.util.module_from_spec(_spec)
    sys.modules[_NAME] = _module  # dataclass + `from __future__ import annotations` cần module đã đăng ký
    _spec.loader.exec_module(_module)

globals().update({k: v for k, v in vars(_module).items() if not k.startswith("__")})
