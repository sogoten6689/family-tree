"""Phiên âm Hán Việt từng chữ, tra từ điển, không gọi dịch vụ ngoài.

Từ điển nằm ở <DOI_CHIEU_DIR>/han_viet.json, dạng {"chữ": ["âm chọn", "âm khác", ...]}, do
tools/tao_tu_dien_han_viet.py tạo. Nguồn là âm đầu mục của Hán Việt tự điển (Thiều Chửu); chữ có nhiều âm
được xếp theo tần suất âm đó xuất hiện trong vế Việt của kho đối chiếu (không đếm tên can chi). Khi tra, âm có
trong vế Việt của chính cặp được chọn trước; ngoài ra không phân biệt được âm theo ngữ cảnh (行 hành/hàng), nên chữ
nhiều âm trả kèm các âm khác để người xem tự chọn.
Chưa có tệp từ điển thì mọi chữ đều không có âm.
"""
from __future__ import annotations

import json
import re
from functools import lru_cache
from pathlib import Path

from app.doi_chieu import service

FILE_NAME = "han_viet.json"


@lru_cache(maxsize=4)
def _load(path_str: str, mtime_ns: int) -> dict[str, list[str]]:
    try:
        data = json.loads(Path(path_str).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}
    if not isinstance(data, dict):
        return {}
    return {
        k: [a for a in v if isinstance(a, str) and a]
        for k, v in data.items()
        if isinstance(k, str) and isinstance(v, list) and any(isinstance(a, str) and a for a in v)
    }


def dictionary() -> dict[str, list[str]]:
    root = service.data_dir()
    path = root / FILE_NAME if root else None
    if path is None or not path.is_file():
        return {}
    return _load(str(path), path.stat().st_mtime_ns)


_WORD_RE = re.compile(r"[^\W\d_]+")


def phien_am(han: str, viet: str = "") -> list[dict]:
    """Từng ký tự của vế Hán: {"c": chữ, "a": âm chọn, "k": [âm khác]}; ký tự không phải chữ Hán hoặc chưa có
    trong từ điển thì chỉ có "c".

    Chữ nhiều âm: nếu vế Việt của cặp có một âm của chữ mà không có âm đầu từ điển thì chọn âm đó
    (戊辰 trong cặp "năm Mậu Thìn" đọc "thìn", 長 trong "Trường Xung" đọc "trường")."""
    table = dictionary()
    words = set(_WORD_RE.findall(viet.lower()))
    out = []
    for ch in han:
        readings = table.get(ch) if service.HAN_RE.fullmatch(ch) else None
        if not readings:
            out.append({"c": ch})
            continue
        if len(readings) > 1 and readings[0] not in words:
            hit = next((r for r in readings[1:] if r in words), None)
            if hit:
                readings = [hit, *(r for r in readings if r != hit)]
        out.append({"c": ch, "a": readings[0], **({"k": readings[1:]} if len(readings) > 1 else {})})
    return out
