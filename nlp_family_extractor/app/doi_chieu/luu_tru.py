"""Tệp JSON có số phiên bản trong thư mục một cuốn (nhận xét, kết quả chấm mẫu).

Ghi nguyên tử; mỗi lần ghi đè, bản cũ được chép vào <cuon>/lich_su/<ten>_<thoi-diem>_v<n>.json.
Lưu với `phien_ban` cũ hơn bản trên máy chủ thì báo VersionConflict, để hai tab không ghi đè nhau.
"""
from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from threading import Lock

HISTORY_DIR = "lich_su"
_write_lock = Lock()


class VersionConflict(Exception):
    """Tệp trên máy chủ đã đổi kể từ lúc tải về."""


def load(bdir: Path, file_name: str, empty: dict) -> dict:
    path = bdir / file_name
    return json.loads(path.read_text(encoding="utf-8")) if path.is_file() else empty


def save(bdir: Path, file_name: str, empty: dict, data: dict, phien_ban: int, nguoi_sua: str) -> dict:
    with _write_lock:
        current = load(bdir, file_name, empty)
        if current.get("phien_ban", 0) != phien_ban:
            raise VersionConflict
        path = bdir / file_name
        if path.is_file():
            history = bdir / HISTORY_DIR
            history.mkdir(exist_ok=True)
            stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
            (history / f"{path.stem}_{stamp}_v{phien_ban}.json").write_text(path.read_text(encoding="utf-8"), encoding="utf-8")
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
