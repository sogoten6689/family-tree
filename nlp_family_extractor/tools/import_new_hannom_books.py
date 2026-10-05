#!/usr/bin/env python3
"""Import 10 new Hán-Nôm books (temple_nom, bulac, nlv_veridian) vào DB.

Từ repo root:
    python nlp_family_extractor/tools/import_new_hannom_books.py --dry-run
    python nlp_family_extractor/tools/import_new_hannom_books.py
"""
from __future__ import annotations

import argparse
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.auth.bootstrap import bootstrap_auth
from app.auth.user_repository import UserRepository
from app.database import database_enabled, init_database, session_scope
from app.documents.bootstrap import bootstrap_documents
from app.workspace.bootstrap import bootstrap_workspace
from app.workspace.models import OcrStatus, TreeStatus
from app.workspace.repository import GiaPhaPageRepository, GiaPhaVersionRepository, UserScanRepository

REQUEST_ID_PREFIX = "hannom-corpus:new-"


def count_images(folder: Path) -> int:
    suffixes = {".jpg", ".jpeg", ".png", ".tif", ".tiff", ".webp"}
    if not folder.is_dir():
        return 0
    return sum(1 for p in folder.rglob("*") if p.is_file() and p.suffix.lower() in suffixes)


def get_page_count(book_path: Path) -> int:
    """Count pages (JPG files) in book directory."""
    pages_dir = book_path / "pages" if (book_path / "pages").is_dir() else book_path
    return count_images(pages_dir)


NEW_BOOKS = [
    {"source": "temple_nom", "folder": "nguyen-khoa-q1", "doc_id": "temple-nguyen-khoa-q1", "title_vn": "Nguyễn Khoa thế phổ (quyển 1)"},
    {"source": "temple_nom", "folder": "nguyen-khoa-q2", "doc_id": "temple-nguyen-khoa-q2", "title_vn": "Nguyễn Khoa thế phổ (quyển 2)"},
    {"source": "bulac", "folder": "ARC.HOANG.105", "doc_id": "bulac-hoang-105", "title_vn": "Gia phả các dòng họ (BULAC 105)"},
    {"source": "bulac", "folder": "ARC.HOANG.119", "doc_id": "bulac-hoang-119", "title_vn": "— (BULAC 119)"},
    {"source": "bulac", "folder": "ARC.HOANG.129", "doc_id": "bulac-hoang-129", "title_vn": "Đoàn thị thực lục (BULAC 129)"},
    {"source": "bulac", "folder": "ARC.HOANG.13", "doc_id": "bulac-hoang-13", "title_vn": "Đoàn thị thực lục (BULAC 13)"},
    {"source": "bulac", "folder": "ARC.HOANG.16", "doc_id": "bulac-hoang-16", "title_vn": "Ngô gia thế phả (BULAC 16)"},
    {"source": "bulac", "folder": "ARC.HOANG.73", "doc_id": "bulac-hoang-73", "title_vn": "Đặng gia thế phả (BULAC 73)"},
    {"source": "bulac", "folder": "ARC.HOANG.76", "doc_id": "bulac-hoang-76", "title_vn": "— (BULAC 76)"},
    {"source": "nlv_veridian", "folder": "nlvnpf-1042", "doc_id": "nlv-1042", "title_vn": "Đỗ tộc gia phả (NLV 1042)"},
]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--owner-email",
        default=os.environ.get("ADMIN_EMAIL", "admin@giapha.com"),
        help="Admin tài khoản import",
    )
    parser.add_argument("--dry-run", action="store_true", help="Chỉ in ra, không ghi DB")
    args = parser.parse_args()

    data_root = Path(__file__).resolve().parents[2] / "data/00_raw/hannom"
    if not data_root.is_dir():
        print(f"Không tìm thấy {data_root}")
        return 1

    init_database()
    if not database_enabled():
        print("Không kết nối được MySQL")
        return 1
    bootstrap_auth()
    bootstrap_documents()
    bootstrap_workspace()

    with session_scope() as db:
        user_repo = UserRepository(db)
        owner = user_repo.get_by_email(args.owner_email)
        if owner is None:
            print(f"Không tìm thấy user '{args.owner_email}'")
            return 1

        scans = UserScanRepository(db)
        pages_repo = GiaPhaPageRepository(db)
        versions_repo = GiaPhaVersionRepository(db)

        imported = 0
        skipped = 0

        for book_spec in NEW_BOOKS:
            doc_id = book_spec["doc_id"]
            source = book_spec["source"]
            folder = book_spec["folder"]
            title = book_spec["title_vn"]
            request_id = f"{REQUEST_ID_PREFIX}{doc_id}"

            book_path = data_root / source / folder
            if not book_path.is_dir():
                print(f"[SKIP] {doc_id} — thư mục không tìm thấy: {book_path}")
                skipped += 1
                continue

            page_count = get_page_count(book_path)
            if page_count == 0:
                print(f"[SKIP] {doc_id} — không có ảnh")
                skipped += 1
                continue

            if args.dry_run:
                print(f"[DRY-RUN] {doc_id} -> {title} ({page_count} trang)")
                continue

            # Tạo UserScan draft
            scan = scans.create(
                user_id=owner.id,
                title=title,
                file_name=doc_id,
                file_type="hannom-corpus",
                page_count=page_count,
                source_text=None,
                hannom_text=None,
                transliteration_text=None,
            )
            scans.update(scan, ocr_status=OcrStatus.PENDING, tree_status=TreeStatus.NONE, request_id=request_id)
            print(f"[OK] {doc_id} -> scan#{scan.id} ({page_count} trang, PENDING)")
            imported += 1

        print(f"\n✅ Import hoàn tất: {imported} cuốn, {skipped} skip")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
