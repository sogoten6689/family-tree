#!/usr/bin/env python3
"""Đưa ảnh từng trang của các bộ gia phả lên MinIO và gắn vào gia_pha_page.

Mỗi gia_pha_page có image_file_key là đường dẫn TƯƠNG ĐỐI (vd
data/00_raw/hannom/bulac/ARC.HOANG.129/pages/001.jpg, ghi khi import corpus).
Script tìm file đó dưới --image-root, upload lên MinIO với key ổn định
gia-pha/{scan_id}/pages/{trang:03d}.jpg (app/workspace/page_images.py), rồi
cập nhật image_file_key = key MinIO. Không đụng file gốc.

Idempotent: trang đã có key MinIO → bỏ qua; object đã có trên MinIO (lần chạy
trước dừng giữa chừng) → không upload lại, chỉ cập nhật DB. Thiếu file ảnh →
báo, không dừng.

Chạy (cần MYSQL_* và MINIO_* như backend — vd trong container backend):

    python3 tools/upload_gia_pha_page_images.py --image-root /tmp/imgroot --dry-run
    python3 tools/upload_gia_pha_page_images.py --image-root /tmp/imgroot
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Any, Callable, Optional

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from sqlalchemy import select  # noqa: E402

from app.workspace.models import GiaPhaPage  # noqa: E402
from app.workspace.page_images import content_type_for, is_storage_key, page_image_key  # noqa: E402


def upload_page_images(
    db: Any,
    *,
    image_root: Path,
    object_exists: Callable[[str], bool],
    upload: Callable[[str, Path, str], None],
    dry_run: bool,
    scan_id: Optional[int] = None,
    log: Callable[[str], None] = print,
) -> dict[str, int]:
    """Trả về thống kê {uploaded, reused, already, missing, unsupported}."""
    stmt = select(GiaPhaPage).order_by(GiaPhaPage.user_scan_id, GiaPhaPage.page_number)
    if scan_id is not None:
        stmt = stmt.where(GiaPhaPage.user_scan_id == scan_id)
    stats = {"uploaded": 0, "reused": 0, "already": 0, "missing": 0, "unsupported": 0}
    for page in db.scalars(stmt).all():
        source = page.image_file_key
        if not source:
            continue
        if is_storage_key(source):
            stats["already"] += 1
            continue
        content_type = content_type_for(source)
        if content_type is None:
            stats["unsupported"] += 1
            log(f"[BỎ QUA] scan#{page.user_scan_id} trang {page.page_number}: định dạng không hỗ trợ ({source})")
            continue
        local = image_root / source
        if not local.is_file():
            stats["missing"] += 1
            log(f"[THIẾU FILE] scan#{page.user_scan_id} trang {page.page_number}: {local}")
            continue
        key = page_image_key(page.user_scan_id, page.page_number, source)
        if object_exists(key):
            stats["reused"] += 1
        else:
            stats["uploaded"] += 1
            if not dry_run:
                upload(key, local, content_type)
        if not dry_run:
            page.image_file_key = key
            db.add(page)
            db.commit()
    return stats


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--image-root", required=True, type=Path, help="Thư mục chứa data/00_raw/… (gốc của đường dẫn tương đối)")
    parser.add_argument("--dry-run", action="store_true", help="Chỉ đếm/báo, không upload, không ghi DB")
    parser.add_argument("--scan-id", type=int, help="Chỉ xử lý 1 bộ gia phả")
    args = parser.parse_args()

    from botocore.exceptions import ClientError

    from app.database import database_enabled, init_database, session_scope
    from app.documents.storage import ObjectStorage

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

    with session_scope() as db:
        stats = upload_page_images(
            db,
            image_root=args.image_root,
            object_exists=object_exists,
            upload=upload,
            dry_run=args.dry_run,
            scan_id=args.scan_id,
        )
    label = "DRY-RUN — " if args.dry_run else ""
    print(
        f"\n{label}Tổng kết: upload mới {stats['uploaded']}, đã có trên MinIO {stats['reused']}, "
        f"đã gắn từ trước {stats['already']}, thiếu file {stats['missing']}, định dạng không hỗ trợ {stats['unsupported']}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
