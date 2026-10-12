"""OCR theo từng engine cho TỪNG TRANG: engine nào đã có kết quả, engine nào chạy bổ sung được.

Tên engine lưu trong `ocr_vote_meta.engines` (kim_hannom_lab, gemini, deepseek, paddle_v6,
google_vision) khác tên engine chạy trên server (kimhannom, gemini_vision, google_vision) nên có
bảng ánh xạ ở đây. deepseek và paddle_v6 hiện chỉ có kết quả nhập từ phòng thí nghiệm — server chưa
có adapter để chạy (xem `runner=None`).
"""
from __future__ import annotations

import copy
from dataclasses import dataclass
from typing import Any, Callable, Dict, List, Optional


@dataclass(frozen=True)
class PageEngine:
    name: str  # tên lưu trong ocr_vote_meta.engines
    label: str
    runner: Optional[str]  # tên hàm chạy trên server (hannom.engines) hoặc None = chưa chạy được
    not_runnable_reason: str = ""
    paid: bool = True


PAGE_ENGINES: List[PageEngine] = [
    PageEngine("kim_hannom_lab", "Kim Hán Nôm Lab", "kimhannom"),
    PageEngine("gemini", "Gemini Vision", "gemini_vision"),
    PageEngine("google_vision", "Google Vision", "google_vision"),
    PageEngine("paddle_v6", "PaddleOCR v6", None, "Server chưa cài PaddleOCR; kết quả hiện chỉ nhập từ phòng thí nghiệm.", paid=False),
    PageEngine("deepseek", "DeepSeek OCR", None, "Chưa có adapter DeepSeek trên server; kết quả hiện chỉ nhập từ phòng thí nghiệm."),
]
BY_NAME: Dict[str, PageEngine] = {e.name: e for e in PAGE_ENGINES}


def runner_for(engine: PageEngine) -> Optional[Callable[..., Any]]:
    from app.hannom import engines

    if engine.runner is None:
        return None
    return engines.ENGINE_REGISTRY.get(engine.runner) or engines.PAGE_ONLY_ENGINES.get(engine.runner)


def readiness(engine: PageEngine) -> tuple[bool, str]:
    """(chạy được ngay không, lý do nếu chưa). Chỉ kiểm cấu hình, không gọi API."""
    if engine.runner is None:
        return False, engine.not_runnable_reason
    if engine.runner == "google_vision":
        import os

        return (True, "") if os.environ.get("GOOGLE_VISION_API_KEY", "").strip() else (False, "Chưa cấu hình GOOGLE_VISION_API_KEY.")
    from app.hannom.engine_config import engine_ready

    ok, reason = engine_ready(engine.runner)
    return ok, reason or ""


def present_engines(meta: Any) -> set[str]:
    engines = meta.get("engines") if isinstance(meta, dict) else None
    if not isinstance(engines, dict):
        return set()
    return {name for name, info in engines.items() if isinstance(info, dict) and (info.get("text") or "").strip()}


def merge_engine_text(meta: Optional[dict], name: str, text: str) -> dict:
    """Thêm kết quả 1 engine vào meta; KHÔNG vote lại và KHÔNG đổi chữ chính của trang."""
    merged = copy.deepcopy(meta) if isinstance(meta, dict) else {}
    engines = merged.setdefault("engines", {})
    if merged.get("schema_version") == 2:
        han = sum(1 for ch in text if "\u3400" <= ch <= "\u9fff" or ch >= "\U00020000")
        engines[name] = {"text": text, "han_chars": han, "voted": False, "excluded": "added-after-vote"}
    else:
        engines[name] = {"text": text, "score": None, "similarity_to_others": None}
    return merged
