"""Kết quả chấm mẫu lỗi (Guideline CV mục 7–8) của một cuốn, lưu trên máy chủ.

Lưu ở <cuon>/cham_mau.json: {"nhan": {"<dong>": {"v": nhãn, "han": ..., "viet": ...}}, "phien_ban", ...}.
Mỗi nhãn giữ kèm nội dung cặp lúc chấm: sinh viên nộp lại mà cặp ở dòng đó đổi thì nhãn cũ không còn
được tính, người hướng dẫn phải chấm lại. Chỉ admin ghi; trang công khai chỉ thấy phần tổng hợp (summary).
"""
from __future__ import annotations

import math
from pathlib import Path

from app.doi_chieu import luu_tru

FILE_NAME = "cham_mau.json"
VERDICTS = ("dung", "OMISSION", "ADDITION", "MISSING")
ERROR_TYPES = ("OMISSION", "ADDITION", "MISSING")
SAMPLE_RATE = 0.05
SAMPLE_MIN = 20


class UnknownLine(ValueError):
    """Nhãn gắn cho dòng không phải cặp hợp lệ của bài nộp hiện tại."""


def empty() -> dict:
    return {"nhan": {}, "phien_ban": 0}


def load(bdir: Path) -> dict:
    return luu_tru.load(bdir, FILE_NAME, empty())


def sample_size(valid: int) -> int:
    """Cỡ mẫu: 5% số cặp hợp lệ, tối thiểu 20 (cuốn ít hơn 20 cặp thì chấm hết). Khớp doiChieuGrading.ts."""
    return min(valid, max(SAMPLE_MIN, math.ceil(valid * SAMPLE_RATE)))


def save(bdir: Path, verdicts: dict[int, str], pairs: list[dict], phien_ban: int, nguoi_sua: str) -> dict:
    by_line = {p["line"]: p for p in pairs if not p["errors"]}
    nhan = {}
    for line, v in sorted(verdicts.items()):
        pair = by_line.get(line)
        if pair is None:
            raise UnknownLine(line)
        nhan[str(line)] = {"v": v, "han": pair["han"], "viet": pair["viet"]}
    return luu_tru.save(bdir, FILE_NAME, empty(), {"nhan": nhan}, phien_ban, nguoi_sua)


def current_verdicts(data: dict, pairs: list[dict]) -> dict[int, str]:
    """Nhãn còn khớp với bài nộp hiện tại (cùng dòng, cùng nội dung, cặp vẫn hợp lệ)."""
    by_line = {p["line"]: p for p in pairs if not p["errors"]}
    out = {}
    for key, item in (data.get("nhan") or {}).items():
        try:
            line = int(key)
        except ValueError:
            continue
        pair = by_line.get(line)
        if pair and pair["han"] == item.get("han") and pair["viet"] == item.get("viet") and item.get("v") in VERDICTS:
            out[line] = item["v"]
    return out


def summary(bdir: Path, pairs: list[dict], threshold: float) -> dict:
    """Tổng hợp công khai: số cặp đã chấm, lỗi theo loại, tỷ lệ lỗi; `dat` khi chấm đủ mẫu và tỷ lệ ≤ ngưỡng."""
    verdicts = current_verdicts(load(bdir), pairs)
    valid = sum(1 for p in pairs if not p["errors"])
    by_type = {t: sum(1 for v in verdicts.values() if v == t) for t in ERROR_TYPES}
    checked = len(verdicts)
    errors = sum(by_type.values())
    need = sample_size(valid)
    rate = round(errors / checked, 3) if checked else None
    complete = valid > 0 and checked >= need
    return {
        "checked": checked,
        "sample": need,
        "errors": errors,
        "by_type": by_type,
        "rate": rate,
        "complete": complete,
        "dat": bool(complete and rate is not None and rate <= threshold),
    }
