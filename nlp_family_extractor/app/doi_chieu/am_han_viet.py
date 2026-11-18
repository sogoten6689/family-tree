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
from collections import Counter
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
# Chữ luôn đọc âm đầu, không đổi theo vế Việt: trong gia phả 卒 hầu như luôn là "tốt" (mất); kiểm thử 18/11/2026
# thấy 13 cặp vẫn đổi sai sang "tuất" vì vế Việt có "Tuất" mà vế Hán không có 戌 (cặp dóng lệch).
LOCKED = {"卒"}
# Địa chi đứng sau thiên can (庚辰) hoặc trước chữ giờ (辰時) là tên chi, đọc theo tên chi dù vế Việt không ghi
# (kiểm thử 18/11/2026: 辰 còn "thần" 44 chỗ vì vế Việt bỏ phần ngày giờ).
STEMS = set("甲乙丙丁戊己庚辛壬癸")
TIME_MARKS = set("時时")
BRANCH_NAMES = {
    "子": ("tý", "tí"), "丑": ("sửu",), "寅": ("dần",), "卯": ("mão", "mẹo"), "辰": ("thìn",), "巳": ("tỵ", "tị"),
    "午": ("ngọ",), "未": ("mùi",), "申": ("thân",), "酉": ("dậu",), "戌": ("tuất",), "亥": ("hợi",),
}


def _branch_reading(han: str, i: int, readings: list[str]) -> str | None:
    ch = han[i]
    if ch not in BRANCH_NAMES:
        return None
    before = han[i - 1] if i > 0 else ""
    after = han[i + 1] if i + 1 < len(han) else ""
    if before not in STEMS and after not in TIME_MARKS:
        return None
    return next((r for r in BRANCH_NAMES[ch] if r in readings), None)


def phien_am(han: str, viet: str = "") -> list[dict]:
    """Từng ký tự của vế Hán: {"c": chữ, "a": âm chọn, "k": [âm khác]}; ký tự không phải chữ Hán hoặc chưa có
    trong từ điển thì chỉ có "c".

    Chữ nhiều âm: nếu vế Việt của cặp có một âm của chữ mà không có âm đầu từ điển thì chọn âm đó
    (戊辰 trong cặp "năm Mậu Thìn" đọc "thìn", 長 trong "Trường Xung" đọc "trường")."""
    table = dictionary()
    words = Counter(_WORD_RE.findall(viet.lower()))
    # Từ trong vế Việt đã có chữ khác của cặp nhận làm âm chính (戌 → "Tuất") thì không dùng để đổi âm chữ này,
    # tránh 卒 thành "tuất" trong cặp "…năm Bính Tuất… 卒".
    claimed = Counter(table[c][0] for c in han if table.get(c))
    out = []
    for i, ch in enumerate(han):
        readings = table.get(ch) if service.HAN_RE.fullmatch(ch) else None
        if not readings:
            out.append({"c": ch})
            continue
        branch = _branch_reading(han, i, readings) if len(readings) > 1 else None
        if branch:
            readings = [branch, *(r for r in readings if r != branch)]
        elif len(readings) > 1 and readings[0] not in words and ch not in LOCKED:
            hit = next((r for r in readings[1:] if words[r] > claimed[r]), None)
            if hit:
                readings = [hit, *(r for r in readings if r != hit)]
        out.append({"c": ch, "a": readings[0], **({"k": readings[1:]} if len(readings) > 1 else {})})
    return out
