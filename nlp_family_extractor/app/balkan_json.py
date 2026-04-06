from __future__ import annotations

import json
import re
from typing import Any, Dict, List


def parse_balkan_json_array(text: str) -> List[Dict[str, Any]]:
    """
    Parse Gemini output into a list of BALKAN node dicts.
    Strips optional ```json fences and can recover a top-level [...] substring.
    """
    raw = text.strip()
    if raw.startswith("```"):
        raw = re.sub(r"^```(?:json)?\s*", "", raw, count=1, flags=re.IGNORECASE)
        raw = re.sub(r"\s*```\s*$", "", raw, count=1)
        raw = raw.strip()

    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        start = raw.find("[")
        end = raw.rfind("]")
        if start == -1 or end == -1 or end <= start:
            raise ValueError("Response is not valid JSON array") from None
        data = json.loads(raw[start : end + 1])

    if not isinstance(data, list):
        raise ValueError("Expected a JSON array of nodes")
    return [x for x in data if isinstance(x, dict)]
