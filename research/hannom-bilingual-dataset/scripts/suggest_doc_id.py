#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Gợi ý 1 doc_id MỚI, đảm bảo không trùng — dùng TRƯỚC khi tạo thư mục inbox.

Không cần biết trước quy_mo/hinh_thuc/dia_danh/nien_dai (những thứ đó xác định
SAU khi đọc tài liệu) — chỉ cần biết Họ nếu đã rõ, hoặc để trống nếu chưa rõ.

Dùng:
  python3 scripts/suggest_doc_id.py --ho "Nguyễn"    # -> nguyen-01 (hoặc -02, -03... nếu đã có)
  python3 scripts/suggest_doc_id.py                  # -> moi-01 (chưa rõ họ, dùng nhóm "moi")

Script này CHỈ ĐỌC books_catalog.json để kiểm tra trùng — không ghi gì cả,
không đăng ký gì. Dùng kết quả in ra làm --doc-id cho add_new_source.py.
"""
from __future__ import annotations

import argparse
import json
import re
import unicodedata
from pathlib import Path

from _repo_paths import FAMILY_TREE

CATALOG_PATH = FAMILY_TREE / "data/00_raw/hannom/books_catalog.json"


def slugify(s: str) -> str:
    # Đ/đ không có decomposition trong Unicode NFKD (khác các dấu khác của
    # tiếng Việt) -> phải thay tay trước, nếu không "Đặng" sẽ rụng mất "Đ".
    s = s.replace("Đ", "D").replace("đ", "d")
    s = unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode("ascii")
    s = s.lower().strip()
    s = re.sub(r"[^a-z0-9]+", "", s)
    return s or "moi"


def suggest(ho: str | None, existing: set[str]) -> str:
    prefix = slugify(ho) if ho else "moi"
    n = 1
    while True:
        candidate = f"{prefix}-{n:02d}"
        if candidate not in existing:
            return candidate
        n += 1


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--ho", default=None, help="Họ nếu đã biết (vd: Nguyễn, Trần, Phan). Bỏ trống nếu chưa rõ.")
    args = ap.parse_args()

    catalog = json.loads(CATALOG_PATH.read_text(encoding="utf-8"))
    existing = {b["book_id"] for b in catalog["books"]}

    candidate = suggest(args.ho, existing)
    print(candidate)
    print()
    print("Dùng id này làm --doc-id (chưa đăng ký gì, chỉ mới gợi ý):")
    ho_flag = f' --ho "{args.ho}"' if args.ho else ""
    print(f'  1. mkdir -p family-tree/data/00_raw/hannom_inbox/{candidate}')
    print(f'     (bỏ ảnh 0.jpg, 1.jpg, ... vào thư mục này)')
    print(f'  2. python3 scripts/add_new_source.py --doc-id {candidate} --title-vn "..."{ho_flag}')
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
