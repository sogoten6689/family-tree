from __future__ import annotations

from typing import Any, Dict, List, Optional

from app.balkan_json import parse_balkan_json_array
from app.balkan_prompt import build_balkan_normalization_prompt
from app.config import GOOGLE_API_KEY
from app.gemini_client import GeminiClient


def normalize_balkan_nodes(
    source_text: str,
    rough_extraction: Optional[Dict[str, Any]] = None,
) -> tuple[List[Dict[str, Any]], Optional[str]]:
    """
    Gọi Gemini để chuẩn hoá văn bản + extract thô thành mảng node BALKAN (id số).

    Returns:
        (nodes, None) khi thành công.
        ([], error_message) khi thiếu key, lỗi API hoặc JSON không parse được.
    """
    if not GOOGLE_API_KEY:
        return [], "Gemini skipped: GOOGLE_API_KEY not set"

    try:
        client = GeminiClient()
        prompt = build_balkan_normalization_prompt(source_text, rough_extraction)
        raw = client.generate(prompt)
        nodes = parse_balkan_json_array(raw)
        return nodes, None
    except ValueError as exc:
        return [], f"Gemini JSON parse error: {exc}"
    except Exception as exc:  # pragma: no cover - API/network
        return [], f"Gemini error: {exc}"


class GeminiService:
    """
    Application-level Gemini entry point.

    Use this for prompts that will later include BALKAN JSON normalization.
    Lower-level access: `GeminiClient` in `app.gemini_client`.
    """

    def __init__(self) -> None:
        self._client = GeminiClient()

    def generate(self, prompt: str) -> str:
        return self._client.generate(prompt)

    def normalize_to_balkan_json(
        self,
        source_text: str,
        rough_extraction: Optional[Dict[str, Any]] = None,
    ) -> str:
        """
        Chuẩn hoá gia phả sang mảng node BALKAN (id số, pids, fid/mid).
        Trả về chuỗi text từ model — cần parse JSON phía gọi (và strip markdown nếu có).
        """
        prompt = build_balkan_normalization_prompt(source_text, rough_extraction)
        return self._client.generate(prompt)
