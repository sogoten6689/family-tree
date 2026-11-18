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


# Chữ đi trong cụm chỉ hướng phong thuỷ (戌山辰向, 子午向, 乙辛兼卯酉向): địa chi ở đây cũng là tên chi.
_DIRECTION_RUN = set("乾坤艮巽山兼") | STEMS | set(BRANCH_NAMES)
# 子 nghĩa "con": sau các chữ này hoặc trước số đếm, 女, 孫 (長子, 次子, 子一, 子女, 子孫).
_SON_BEFORE = set("長长次嗣之幼諸诸男孫孙庶養养繼继")
_SON_AFTER = set("一二三四五六七八九十女孫孙")


def _branch_reading(han: str, i: int, readings: list[str]) -> str | None:
    ch = han[i]
    if ch not in BRANCH_NAMES:
        return None
    before = han[i - 1] if i > 0 else ""
    after = han[i + 1] if i + 1 < len(han) else ""
    is_branch = before in STEMS or after in TIME_MARKS
    if not is_branch:
        j = i + 1
        while j < len(han) and j <= i + 4 and han[j] in _DIRECTION_RUN:
            j += 1
        is_branch = j < len(han) and han[j] == "向"
    if not is_branch:
        return None
    return next((r for r in BRANCH_NAMES[ch] if r in readings), None)


def _fixed_reading(han: str, i: int, readings: list[str]) -> str | None:
    """Âm quyết định được từ chính vế Hán, không cần nhìn vế Việt; None là để vế Việt quyết định."""
    ch = han[i]
    if len(readings) == 1 or ch in LOCKED:
        return readings[0]
    if ch == "子" and "tử" in readings:
        before = han[i - 1] if i > 0 else ""
        after = han[i + 1] if i + 1 < len(han) else ""
        if before in _SON_BEFORE or after in _SON_AFTER:
            return "tử"
    return _branch_reading(han, i, readings)


def phien_am(han: str, viet: str = "") -> list[dict]:
    """Từng ký tự của vế Hán: {"c": chữ, "a": âm chọn, "k": [âm khác]}; ký tự không phải chữ Hán hoặc chưa có
    trong từ điển thì chỉ có "c".

    Thứ tự quyết định âm của chữ nhiều âm:
    1. Ngữ cảnh trong vế Hán: khoá (卒), 子 nghĩa "con" (長子, 子一), địa chi trong can chi/giờ/hướng (庚辰, 辰時, 辰向).
    2. Vế Việt của cặp: âm đầu có trong vế Việt thì giữ; không thì lấy âm khác có trong vế Việt (戊辰 "Mậu Thìn" → thìn,
       長冲 "Trường Xung" → trường). Mỗi lần xuất hiện của một từ trong vế Việt chỉ dùng cho một chữ, và từ đã thuộc
       về chữ khác của cặp (戌 → "Tuất") thì không dùng lại.
    3. Còn lại: âm đầu từ điển."""
    table = dictionary()
    words = Counter(_WORD_RE.findall(viet.lower()))
    cells = [table.get(ch) if service.HAN_RE.fullmatch(ch) else None for ch in han]
    chosen: list[str | None] = [None] * len(han)
    claimed: Counter = Counter()
    for i, readings in enumerate(cells):
        if not readings:
            continue
        fixed = _fixed_reading(han, i, readings)
        if fixed:
            chosen[i] = fixed
            claimed[fixed] += 1
        elif readings[0] in words:
            chosen[i] = readings[0]
            claimed[readings[0]] += 1
    for i, readings in enumerate(cells):
        if not readings or chosen[i]:
            continue
        hit = next((r for r in readings[1:] if words[r] > claimed[r]), None)
        if hit:
            claimed[hit] += 1
        chosen[i] = hit or readings[0]
    out = []
    for ch, readings, a in zip(han, cells, chosen):
        if not readings:
            out.append({"c": ch})
            continue
        rest = [r for r in readings if r != a]
        out.append({"c": ch, "a": a, **({"k": rest} if rest else {})})
    return out
