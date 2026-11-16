"""Nhận xét của người hướng dẫn cho bài nộp của một cuốn (chỉ admin đọc và ghi).

Lưu ở <cuon>/nhan_xet.json, tách khỏi bài nộp và nháp soát. Trang đối chiếu công khai không đọc tệp này,
để nhận xét về một bạn không lộ cho người khác. Bản cũ được giữ trong <cuon>/lich_su/ mỗi lần lưu.
"""
from __future__ import annotations

from pathlib import Path

from app.doi_chieu import luu_tru
from app.doi_chieu.luu_tru import VersionConflict

FILE_NAME = "nhan_xet.json"

__all__ = ["FILE_NAME", "VersionConflict", "empty", "load", "save"]


def empty() -> dict:
    return {"trang_thai": "nhap", "mo_dau": "", "muc": [], "ket": "", "phien_ban": 0}


def load(bdir: Path) -> dict:
    return luu_tru.load(bdir, FILE_NAME, empty())


def save(bdir: Path, data: dict, phien_ban: int, nguoi_sua: str) -> dict:
    return luu_tru.save(bdir, FILE_NAME, empty(), data, phien_ban, nguoi_sua)
