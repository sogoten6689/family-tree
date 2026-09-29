#!/usr/bin/env python3
"""Đính ảnh/file gốc (đã upload sẵn vào MinIO ở 1 prefix staging cố định) vào
cây gia phả tương ứng cho các UserScan mà `import_hannom_bilingual_corpus.py`
đã tạo — bước 2 của việc đưa corpus Hán Nôm vào hệ quản lý gia phả thật (bước
1 là text/OCR/vote, xem tools/import_hannom_bilingual_corpus.py).

QUY ƯỚC THƯ MỤC STAGING (bắt buộc để script này tìm đúng file — không cần đổi
tên/tổ chức lại gì, chỉ MIRROR CHÍNH XÁC cây thư mục `data/00_raw/` đã có sẵn
trong repo `hannom-bilingual-dataset`, đổi duy nhất tiền tố):

    data/00_raw/<phần còn lại>
        -> upload thành ->
    s3://<MINIO_BUCKET>/hannom-corpus-staging/<phần còn lại>   (giữ nguyên)

Ví dụ record "nom-1158" (`nguon.duong_dan_goc` =
"data/00_raw/hannom/nomfoundation/volumes/1158", ảnh từng trang tại
".../volumes/1158/pages/001.jpg", "002.jpg", ...) — upload thành:

    s3://<bucket>/hannom-corpus-staging/hannom/nomfoundation/volumes/1158/pages/001.jpg
    s3://<bucket>/hannom-corpus-staging/hannom/nomfoundation/volumes/1158/pages/002.jpg
    ...

Với `mc` (MinIO client, đã `mc alias set` sẵn), từ thư mục chứa `data/00_raw/`:

    mc cp -r data/00_raw/ myminio/<bucket>/hannom-corpus-staging/

Không cần biết trước document_id hay bất kỳ UUID nào — key thật trong bucket
(dùng lâu dài, khác staging) do `DocumentService.build_file_key` tự sinh khi
script này chạy, giống hệt code path app đang dùng cho upload thật (không tự
chế key S3 tay).

Sau khi upload xong lên staging, chạy script này:

  1. Với mỗi UserScan đã import trước (request_id "hannom-corpus:<doc_id>"),
     tính đúng (các) key staging kỳ vọng từ `l0_image`/`nguon.duong_dan_goc`
     của record, kiểm tra tồn tại thật trong bucket (HEAD, không đoán).
  2. Nếu scan CHƯA có FamilyTree (chưa cấu hình GOOGLE_API_KEY, hoặc Gemini
     trích xuất thất bại) — tự tạo 1 tree rỗng (nodes=[], is_public=True) để
     có chỗ gắn ảnh, không bỏ sót ảnh chỉ vì chưa trích xuất được quan hệ.
  3. Tạo 1 Document (type=HINH_ANH cho ảnh scan nhiều trang, VAN_BAN cho file
     nguồn .docx/.pdf đơn) + 1 DocumentFile cho mỗi ảnh/file tìm thấy, qua
     đúng `DocumentService.upload_files` (đọc bytes từ staging, ghi vào key
     thật, tạo DB row) — không đụng file gốc trong data/00_raw trên máy bạn.
  4. Idempotent theo Document.description marker (cùng kiểu với
     app/nomfoundation/sync_nomfoundation_documents.py) — chạy lại không tạo
     trùng, chỉ bù file còn thiếu nếu lần trước bị dở dang.

KHÔNG xoá object staging sau khi đính — giữ nguyên trong bucket làm bản sao
dự phòng (bạn tự dọn bằng `mc rm -r` nếu muốn, sau khi xác nhận đã đính đủ).

Chạy (từ nlp_family_extractor/, cần MYSQL_HOST/... + MINIO_*/S3_* env, giống
khi chạy `uvicorn api:app`):

    python3 tools/attach_hannom_corpus_images.py --dry-run   # chỉ liệt kê
    python3 tools/attach_hannom_corpus_images.py             # đính thật
"""
from __future__ import annotations

import argparse
import glob
import json
import mimetypes
import os
import sys
from io import BytesIO
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

ROOT = Path(__file__).resolve().parents[1]  # nlp_family_extractor/
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from botocore.exceptions import ClientError  # noqa: E402
from sqlalchemy import select  # noqa: E402

from app.auth.bootstrap import bootstrap_auth  # noqa: E402
from app.auth.user_repository import UserRepository  # noqa: E402
from app.database import database_enabled, init_database, session_scope  # noqa: E402
from app.documents.bootstrap import bootstrap_documents  # noqa: E402
from app.documents.models import Document, DocumentType  # noqa: E402
from app.documents.repository import DocumentRepository, DocumentService  # noqa: E402
from app.documents.storage import ObjectStorage, ObjectStorageError  # noqa: E402
from app.family_tree_store import (  # noqa: E402
    JsonFamilyTreeStore,
    MirroredFamilyTreeStore,
    MySqlFamilyTreeStore,
)
from app.workspace.bootstrap import bootstrap_workspace  # noqa: E402
from app.workspace.repository import UserScanRepository  # noqa: E402

REQUEST_ID_PREFIX = "hannom-corpus:"
RAW_PREFIX = "data/00_raw/"
STAGING_PREFIX = "hannom-corpus-staging/"
IMAGES_MARKER_PREFIX = "hannom-corpus-images="


def _default_data_root() -> Path:
    override = os.environ.get("HANNOM_DATA_ROOT")
    if override:
        return Path(override)
    return ROOT.parent.parent / "hannom-bilingual-dataset"


def _create_family_tree_store():
    source_store = JsonFamilyTreeStore(ROOT / "data" / "family_trees")
    try:
        mysql_store = MySqlFamilyTreeStore.from_env()
        return MirroredFamilyTreeStore(primary_store=mysql_store, source_store=source_store)
    except Exception:
        return source_store


def load_records(data_root: Path) -> Dict[str, Dict[str, Any]]:
    records: Dict[str, Dict[str, Any]] = {}
    pattern = str(data_root / "data" / "*" / "*.json")
    for path in sorted(glob.glob(pattern)):
        with open(path, "r", encoding="utf-8") as f:
            record = json.load(f)
        doc_id = record.get("doc_id")
        if doc_id:
            records[doc_id] = record
    return records


def _staging_key(raw_relative_path: str) -> Optional[str]:
    """`data/00_raw/x/y.jpg` -> `hannom-corpus-staging/x/y.jpg`. None nếu
    path không theo đúng quy ước (không tự đoán/sửa)."""
    if not raw_relative_path.startswith(RAW_PREFIX):
        return None
    return STAGING_PREFIX + raw_relative_path[len(RAW_PREFIX):]


def _expected_files(record: Dict[str, Any]) -> List[Tuple[str, str]]:
    """Trả về [(staging_key, file_name), ...] kỳ vọng cho record — ưu tiên
    ảnh từng trang (l0_image) nếu có trang nào có; nếu không, fallback về
    đúng 1 file nguồn (nguon.duong_dan_goc, khi nó trỏ vào 1 FILE — có đuôi
    mở rộng nhận diện được, không phải thư mục)."""
    pages = record.get("pages") or []
    page_files: List[Tuple[str, str]] = []
    for page in pages:
        image_path = page.get("l0_image")
        if not image_path:
            continue
        key = _staging_key(image_path)
        if key:
            page_files.append((key, Path(image_path).name))
    if page_files:
        return page_files

    nguon = record.get("nguon") or {}
    raw_path = nguon.get("duong_dan_goc")
    if raw_path and Path(raw_path).suffix:  # có đuôi mở rộng => là file, không phải thư mục
        key = _staging_key(raw_path)
        if key:
            return [(key, Path(raw_path).name)]
    return []


def _guess_content_type(file_name: str) -> str:
    guessed, _ = mimetypes.guess_type(file_name)
    return guessed or "application/octet-stream"


def _doc_type_for(record: Dict[str, Any], files: List[Tuple[str, str]]) -> DocumentType:
    if len(files) > 1 or (files and Path(files[0][1]).suffix.lower() in {".jpg", ".jpeg", ".png", ".webp"}):
        return DocumentType.HINH_ANH
    return DocumentType.VAN_BAN


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument(
        "--owner-email",
        default=os.environ.get("ADMIN_EMAIL", "admin@giapha.com"),
        help="Tài khoản sở hữu scan đã import trước (mặc định: admin@giapha.com)",
    )
    parser.add_argument("--dry-run", action="store_true", help="Chỉ liệt kê, không ghi DB/MinIO")
    args = parser.parse_args()

    data_root = _default_data_root()
    records = load_records(data_root)
    if not records:
        print(f"Không tìm thấy record nào ở {data_root}/data/*/*.json — kiểm tra HANNOM_DATA_ROOT.")
        return 1

    init_database()
    if not database_enabled():
        print("Không kết nối được MySQL — dừng.")
        return 1
    bootstrap_auth()
    bootstrap_documents()
    bootstrap_workspace()

    storage = ObjectStorage.from_env()
    if not storage.config.enabled:
        print("Thiếu MINIO_ENDPOINT/MINIO_ACCESS_KEY/MINIO_SECRET_KEY/MINIO_BUCKET — dừng.")
        return 1
    try:
        storage.ensure_bucket()
    except ObjectStorageError as exc:
        print(f"Không truy cập được bucket MinIO: {exc}")
        return 1

    store = _create_family_tree_store()

    with session_scope() as db:
        owner = UserRepository(db).get_by_email(args.owner_email)
        if owner is None:
            print(f"Không tìm thấy user '{args.owner_email}'.")
            return 1

        scans = UserScanRepository(db)
        scans_by_doc_id = {
            scan.request_id[len(REQUEST_ID_PREFIX):]: scan
            for scan in scans.list_by_user(owner.id)
            if scan.request_id and scan.request_id.startswith(REQUEST_ID_PREFIX)
        }
        if not scans_by_doc_id:
            print(
                "Không có UserScan nào đã import từ corpus (chạy "
                "tools/import_hannom_bilingual_corpus.py trước)."
            )
            return 1

        doc_repository = DocumentRepository(db)
        service = DocumentService(doc_repository, storage, get_tree=store.get_tree)

        attached, missing_files, no_tree_created, skipped_dup, skipped_no_files = 0, 0, 0, 0, 0

        for doc_id, scan in scans_by_doc_id.items():
            record = records.get(doc_id)
            if record is None:
                continue

            expected = _expected_files(record)
            if not expected:
                skipped_no_files += 1
                continue

            found: List[Tuple[str, str]] = []
            for key, file_name in expected:
                try:
                    storage.internal_client.head_object(Bucket=storage.config.bucket, Key=key)
                    found.append((key, file_name))
                except ClientError:
                    pass

            if not found:
                print(
                    f"[CHƯA CÓ STAGING] {doc_id}: kỳ vọng {len(expected)} file ở "
                    f"{STAGING_PREFIX}... — chưa upload hoặc sai đường dẫn."
                )
                missing_files += 1
                continue

            if len(found) < len(expected):
                print(
                    f"[THIẾU 1 PHẦN] {doc_id}: tìm thấy {len(found)}/{len(expected)} file staging "
                    f"— vẫn đính phần đã có, phần thiếu bỏ qua."
                )

            title = scan.title
            marker = f"{IMAGES_MARKER_PREFIX}{doc_id}"

            if scan.family_tree_id is None:
                if args.dry_run:
                    print(f"[DRY-RUN] {doc_id}: sẽ tạo tree rỗng trước khi đính {len(found)} file")
                    continue
                tree = store.create_tree(
                    name=title,
                    description=record.get("dia_danh") or None,
                    nodes=[],
                    has_source_document=True,
                    has_hannom_text=bool(record.get("co_ban_han")),
                    user_id=owner.id,
                    is_public=True,
                )
                scans.update(scan, family_tree_id=tree["id"])
                no_tree_created += 1
                family_tree_id = tree["id"]
            else:
                family_tree_id = scan.family_tree_id

            if args.dry_run:
                print(f"[DRY-RUN] {doc_id} -> tree {family_tree_id}, đính {len(found)} file")
                continue

            existing = db.scalar(
                select(Document).where(
                    Document.family_tree_id == family_tree_id,
                    Document.description == marker,
                )
            )
            if existing is not None and len(existing.files) >= len(found):
                print(f"[SKIP đã đính] {doc_id} -> document#{existing.id} ({len(existing.files)} file)")
                skipped_dup += 1
                continue

            document = existing or doc_repository.create(
                family_tree_id=family_tree_id,
                title=f"Ảnh/file gốc — {title}",
                description=marker,
                doc_type=_doc_type_for(record, found),
                subtype="hannom-corpus",
            )
            existing_names = {f.file_name for f in (document.files or [])}

            uploads: List[Tuple[str, str, BytesIO, int]] = []
            for key, file_name in found:
                if file_name in existing_names:
                    continue
                content = storage.read_file_bytes(key)
                uploads.append((file_name, _guess_content_type(file_name), BytesIO(content), len(content)))

            if not uploads:
                print(f"[SKIP không có file mới] {doc_id} -> document#{document.id}")
                skipped_dup += 1
                continue

            created = service.upload_files(document.id, uploads)
            print(f"[OK] {doc_id} -> document#{document.id}, đính {len(created)} file")
            attached += 1

        print(
            "\nTổng kết — "
            f"đã đính: {attached}, tree rỗng mới tạo (để có chỗ gắn ảnh): {no_tree_created}, "
            f"chưa có file trên staging: {missing_files}, đã đính trước (skip): {skipped_dup}, "
            f"record không có ảnh/file nguồn để đính: {skipped_no_files}, "
            f"tổng scan đã import: {len(scans_by_doc_id)}"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
