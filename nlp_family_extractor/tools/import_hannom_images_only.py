#!/usr/bin/env python3
"""Đưa các cuốn gia phả Hán Nôm lên web CHỈ với ảnh, CHƯA OCR (không tốn tiền).

Mỗi cuốn: tạo 1 bộ (user_scans, ocr_status=PENDING), 1 version, các trang (gia_pha_page) rồi đẩy ảnh lên MinIO
(dùng lại upload_page_images). Chạy lại an toàn: cuốn đã có (theo request_id) thì bỏ qua; ảnh đã lên thì không đẩy lại.

Chạy trong container backend (có sẵn DB + MinIO), với thư mục ảnh gắn tại --image-root:
    python tools/import_hannom_images_only.py --image-root /data --dry-run
    python tools/import_hannom_images_only.py --image-root /data [--only nom-595,nom-716]
"""
from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from sqlalchemy import select  # noqa: E402

from app.workspace.models import OcrStatus, TreeStatus, UserScan  # noqa: E402
from app.workspace.repository import GiaPhaPageRepository, GiaPhaVersionRepository, UserScanRepository  # noqa: E402

REQUEST_ID_PREFIX = "hannom-corpus:img-"
IMAGE_SUFFIXES = {".jpg", ".jpeg", ".png", ".tif", ".tiff", ".webp"}

# (doc_id, thư mục ảnh tương đối trong data/00_raw/hannom, tên hiển thị)
BOOKS: List[Dict[str, str]] = [
    {"doc_id": "nom-595", "folder": "nomfoundation/volumes/595/pages", "title": "Tả Thanh Oai Ngô tộc tổ mộ"},
    {"doc_id": "nom-716", "folder": "nomfoundation/volumes/716/pages", "title": "Chu tộc hậu kỵ"},
    {"doc_id": "temple-nguyen-khoa-q1", "folder": "temple_nom/nguyen-khoa-q1/pages", "title": "Nguyễn Khoa thế phổ (quyển 1)"},
    {"doc_id": "temple-nguyen-khoa-q2", "folder": "temple_nom/nguyen-khoa-q2/pages", "title": "Nguyễn Khoa thế phổ (quyển 2)"},
    {"doc_id": "bulac-hoang-105", "folder": "bulac/ARC.HOANG.105/pages", "title": "Gia phả các dòng họ (BULAC 105)"},
    {"doc_id": "bulac-hoang-119", "folder": "bulac/ARC.HOANG.119/pages", "title": "Gia phả (BULAC 119)"},
    {"doc_id": "bulac-hoang-129", "folder": "bulac/ARC.HOANG.129/pages", "title": "Đoàn thị thực lục (BULAC 129)"},
    {"doc_id": "bulac-hoang-13", "folder": "bulac/ARC.HOANG.13/pages", "title": "Đoàn thị thực lục (BULAC 13)"},
    {"doc_id": "bulac-hoang-16", "folder": "bulac/ARC.HOANG.16/pages", "title": "Ngô gia thế phả (BULAC 16)"},
    {"doc_id": "bulac-hoang-73", "folder": "bulac/ARC.HOANG.73/pages", "title": "Đặng gia thế phả (BULAC 73)"},
    {"doc_id": "bulac-hoang-76", "folder": "bulac/ARC.HOANG.76/pages", "title": "Gia phả (BULAC 76)"},
    {"doc_id": "nlv-1042", "folder": "nlv_veridian/nlvnpf-1042/pages", "title": "Đỗ tộc gia phả (NLV 1042)"},
]


def list_images(folder: Path) -> List[Path]:
    """Ảnh trang theo thứ tự tên; bỏ ảnh xem trước khung chữ và tệp ẩn."""
    if not folder.is_dir():
        return []
    return sorted(
        p for p in folder.iterdir()
        if p.is_file() and p.suffix.lower() in IMAGE_SUFFIXES and "boundingbox" not in p.name.lower() and not p.name.startswith(".")
    )


def import_books(
    db: Any,
    *,
    owner_id: int,
    hannom_root: Path,
    relative_to: Path,
    books: List[Dict[str, str]] = BOOKS,
    dry_run: bool = False,
    log: Callable[[str], None] = print,
) -> Dict[str, Any]:
    """Tạo bộ + version + trang (image_file_key = đường dẫn tương đối, chưa phải khoá MinIO). Trả về thống kê và scan_id đã tạo."""
    scans, versions, pages = UserScanRepository(db), GiaPhaVersionRepository(db), GiaPhaPageRepository(db)
    stats: Dict[str, Any] = {"created": 0, "existing": 0, "empty": 0, "pages": 0, "scan_ids": []}
    for book in books:
        request_id = f"{REQUEST_ID_PREFIX}{book['doc_id']}"
        existing = db.scalar(select(UserScan).where(UserScan.request_id == request_id))
        if existing is not None:
            stats["existing"] += 1
            log(f"[ĐÃ CÓ] {book['doc_id']} -> scan#{existing.id}")
            continue
        images = list_images(hannom_root / book["folder"])
        if not images:
            stats["empty"] += 1
            log(f"[KHÔNG CÓ ẢNH] {book['doc_id']}: {hannom_root / book['folder']}")
            continue
        if dry_run:
            log(f"[DRY-RUN] {book['doc_id']} · {book['title']} · {len(images)} ảnh")
            stats["pages"] += len(images)
            continue
        scan = scans.create(user_id=owner_id, title=book["title"], file_name=book["doc_id"], file_type="hannom-corpus", page_count=len(images))
        scans.update(scan, ocr_status=OcrStatus.PENDING, tree_status=TreeStatus.NONE, request_id=request_id)
        versions.create_version(user_scan_id=scan.id, make_current=True, note="Nhập chỉ ảnh, chưa OCR")
        for number, image in enumerate(images, start=1):
            pages.create_page(user_scan_id=scan.id, page_number=number, image_file_key=image.relative_to(relative_to).as_posix())
        stats["created"] += 1
        stats["pages"] += len(images)
        stats["scan_ids"].append(scan.id)
        log(f"[OK] {book['doc_id']} -> scan#{scan.id} · {len(images)} trang")
    return stats


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--image-root", required=True, type=Path, help="Thư mục chứa hannom/ (gốc của đường dẫn tương đối ảnh)")
    parser.add_argument("--owner-email", default=os.environ.get("ADMIN_EMAIL", "admin@giapha.com"))
    parser.add_argument("--only", help="Danh sách doc_id, cách nhau dấu phẩy")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    from botocore.exceptions import ClientError

    from app.auth.user_repository import UserRepository
    from app.database import database_enabled, init_database, session_scope
    from app.documents.storage import ObjectStorage
    from tools.upload_gia_pha_page_images import upload_page_images

    init_database()
    if not database_enabled():
        print("Không kết nối được MySQL — dừng.")
        return 1
    storage = ObjectStorage.from_env()
    if not storage.config.enabled:
        print("MinIO chưa cấu hình (MINIO_*) — dừng.")
        return 1
    storage.ensure_bucket()

    def object_exists(key: str) -> bool:
        try:
            storage.internal_client.head_object(Bucket=storage.config.bucket, Key=key)
            return True
        except ClientError:
            return False

    def upload(key: str, path: Path, content_type: str) -> None:
        with path.open("rb") as fh:
            storage.upload_file(key, fh, content_type=content_type, size=path.stat().st_size)

    wanted = {x.strip() for x in args.only.split(",")} if args.only else None
    books = [b for b in BOOKS if wanted is None or b["doc_id"] in wanted]
    with session_scope() as db:
        owner = UserRepository(db).get_by_email(args.owner_email)
        if owner is None:
            print(f"Không tìm thấy user '{args.owner_email}'")
            return 1
        stats = import_books(db, owner_id=owner.id, hannom_root=args.image_root / "hannom", relative_to=args.image_root, books=books, dry_run=args.dry_run)
        print(f"{'DRY-RUN — ' if args.dry_run else ''}tạo {stats['created']} bộ · đã có {stats['existing']} · không có ảnh {stats['empty']} · {stats['pages']} trang")
        if not args.dry_run:
            for scan_id in stats["scan_ids"]:
                up = upload_page_images(db, image_root=args.image_root, object_exists=object_exists, upload=upload, dry_run=False, scan_id=scan_id)
                print(f"  scan#{scan_id}: {up}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
