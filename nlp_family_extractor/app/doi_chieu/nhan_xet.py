"""Nhận xét của người hướng dẫn cho bài nộp của một cuốn (chỉ admin đọc và ghi).

Lưu ở <cuon>/nhan_xet.json, tách khỏi bài nộp và nháp soát. Trang đối chiếu công khai không đọc tệp này,
để nhận xét về một bạn không lộ cho người khác. Bản cũ được giữ trong <cuon>/lich_su/ mỗi lần lưu.
"""
from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from threading import Lock

FILE_NAME = "nhan_xet.json"
HISTORY_DIR = "lich_su"
_write_lock = Lock()


class VersionConflict(Exception):
    """Nhận xét trên máy chủ đã đổi kể từ lúc tải về."""


def empty() -> dict:
    return {"trang_thai": "nhap", "mo_dau": "", "muc": [], "ket": "", "phien_ban": 0}


def load(bdir: Path) -> dict:
    path = bdir / FILE_NAME
    return json.loads(path.read_text(encoding="utf-8")) if path.is_file() else empty()


def save(bdir: Path, data: dict, phien_ban: int, nguoi_sua: str) -> dict:
    with _write_lock:
        current = load(bdir)
        if current["phien_ban"] != phien_ban:
            raise VersionConflict
        path = bdir / FILE_NAME
        if path.is_file():
            history = bdir / HISTORY_DIR
            history.mkdir(exist_ok=True)
            stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
            (history / f"nhan_xet_{stamp}_v{phien_ban}.json").write_text(path.read_text(encoding="utf-8"), encoding="utf-8")
        saved = {
            **data,
            "phien_ban": phien_ban + 1,
            "nguoi_sua": nguoi_sua,
            "luu_luc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        }
        tmp = path.with_name(path.name + ".tmp")
        tmp.write_text(json.dumps(saved, ensure_ascii=False, indent=1), encoding="utf-8")
        os.replace(tmp, path)
    return saved
