#!/usr/bin/env python3
"""Import dữ liệu Hán Nôm đã xử lý (repo `hannom-bilingual-dataset`, dữ liệu
thật — xem `research/hannom-bilingual-dataset/scripts/_repo_paths.py` cho quy
ước `HANNOM_DATA_ROOT`) vào hệ quản lý gia phả thật của app này (`UserScan` +
`FamilyTree`, MySQL) — thay cho việc 2 hệ thống này đang hoàn toàn tách biệt.

Mỗi record trở thành 1 UserScan (title/text đã OCR+dịch sẵn, ocr_status=
completed) thuộc về 1 tài khoản cố định (--owner-email). Nếu trích xuất được
quan hệ nhân vật (cần GOOGLE_API_KEY — xem app/gemini_service.py), tạo thêm 1
FamilyTree công khai (is_public=True, xuất hiện ở "Gia phả mẫu"/`/gia-pha`)
và gắn family_tree_id + tree_status=created vào scan. KHÔNG có
GOOGLE_API_KEY: vẫn import scan/text (trung thực, không giả vờ có cây) —
tree_status giữ NONE, in rõ lý do.

KHÔNG xử lý ảnh gốc (nguon.duong_dan_goc trỏ vào family-tree/data/, hiện
chưa có trong môi trường chạy import lần đầu) — chạy riêng 1 lượt đính ảnh
sau khi có access tới file gốc thật (DocumentFile/ObjectStorage, xem
app/documents/repository.py DocumentService.upload_files).

Idempotent: mỗi lần chạy lại, record đã import trước (khớp theo doc_id, lưu
trong UserScan.request_id với prefix "hannom-corpus:") sẽ được bỏ qua, không
tạo trùng.

Chạy (từ nlp_family_extractor/, cần MYSQL_HOST/MYSQL_USER/MYSQL_PASSWORD +
optionally GOOGLE_API_KEY trong env, giống khi chạy `uvicorn api:app`):

    python3 tools/import_hannom_bilingual_corpus.py --dry-run   # xem trước
    python3 tools/import_hannom_bilingual_corpus.py             # import thật
"""
from __future__ import annotations

import argparse
import glob
import json
import os
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

ROOT = Path(__file__).resolve().parents[1]  # nlp_family_extractor/
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.auth.bootstrap import bootstrap_auth  # noqa: E402
from app.auth.user_repository import UserRepository  # noqa: E402
from app.database import database_enabled, init_database, session_scope  # noqa: E402
from app.documents.bootstrap import bootstrap_documents  # noqa: E402
from app.domains.extraction.extractor import FamilyExtractor  # noqa: E402
from app.workspace.bootstrap import bootstrap_workspace  # noqa: E402
from app.family_tree_store import (  # noqa: E402
    JsonFamilyTreeStore,
    MirroredFamilyTreeStore,
    MySqlFamilyTreeStore,
)
from app.gemini_service import normalize_balkan_nodes  # noqa: E402
from app.workspace.models import OcrStatus, TreeStatus  # noqa: E402
from app.workspace.repository import UserScanRepository  # noqa: E402

REQUEST_ID_PREFIX = "hannom-corpus:"


def _default_data_root() -> Path:
    override = os.environ.get("HANNOM_DATA_ROOT")
    if override:
        return Path(override)
    # ROOT = .../family-tree/nlp_family_extractor -> parent = .../family-tree
    # -> sibling repo dữ liệu, đúng quy ước của research/hannom-bilingual-dataset/scripts/_repo_paths.py
    return ROOT.parent.parent / "hannom-bilingual-dataset"


def _create_family_tree_store():
    """Bootstrap giống hệt `api.py:_create_family_tree_store()` — MySQL thật
    nếu có, fallback JSON cục bộ nếu không (để --dry-run/dev chạy được mà
    không cần MySQL)."""
    source_store = JsonFamilyTreeStore(ROOT / "data" / "family_trees")
    try:
        mysql_store = MySqlFamilyTreeStore.from_env()
        return MirroredFamilyTreeStore(primary_store=mysql_store, source_store=source_store)
    except Exception:
        return source_store


def _best_text(record: Dict[str, Any]) -> Optional[str]:
    """Ưu tiên dịch nghĩa (Việt) > phiên âm (Quốc ngữ) > OCR Hán thô — dùng
    văn bản CON NGƯỜI ĐỌC ĐƯỢC tốt nhất sẵn có để trích xuất quan hệ, ghép
    theo đúng thứ tự trang."""
    pages = record.get("pages") or []
    if not pages:
        return None
    parts: List[str] = []
    for page in pages:
        text = page.get("l3_dich_nghia") or page.get("l2_phien_am")
        if not text:
            l1 = page.get("l1_ocr")
            if isinstance(l1, dict):
                text = l1.get("voted_text")
        if text:
            parts.append(text.strip())
    joined = "\n\n".join(p for p in parts if p)
    return joined or None


def _title(record: Dict[str, Any]) -> str:
    return (
        record.get("ten_han_viet")
        or record.get("ten_goc_han")
        or record.get("doc_id")
        or "Gia phả Hán Nôm (chưa đặt tên)"
    )


def load_records(data_root: Path) -> List[Dict[str, Any]]:
    records: List[Dict[str, Any]] = []
    pattern = str(data_root / "data" / "*" / "*.json")
    for path in sorted(glob.glob(pattern)):
        with open(path, "r", encoding="utf-8") as f:
            records.append(json.load(f))
    return records


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--owner-email",
        default=os.environ.get("ADMIN_EMAIL", "admin@giapha.com"),
        help="Tài khoản sở hữu các UserScan/FamilyTree import vào (mặc định: admin@giapha.com)",
    )
    parser.add_argument("--dry-run", action="store_true", help="Chỉ in ra, không ghi DB")
    args = parser.parse_args()

    data_root = _default_data_root()
    records = load_records(data_root)
    if not records:
        print(f"Không tìm thấy record nào ở {data_root}/data/*/*.json — kiểm tra HANNOM_DATA_ROOT.")
        return 1
    print(f"Đọc {len(records)} record từ {data_root}/data/")

    init_database()
    if not database_enabled():
        print("Không kết nối được MySQL (thiếu MYSQL_HOST/MYSQL_USER/MYSQL_PASSWORD) — dừng.")
        return 1
    # Idempotent (CREATE TABLE IF NOT EXISTS) — giống hệt lifespan startup của
    # api.py, để script tự đủ điều kiện chạy mà không cần app đã chạy trước.
    bootstrap_auth()
    bootstrap_documents()
    bootstrap_workspace()

    with session_scope() as db:
        user_repo = UserRepository(db)
        owner = user_repo.get_by_email(args.owner_email)
        if owner is None:
            print(f"Không tìm thấy user '{args.owner_email}' trong DB — tạo tài khoản này trước khi import.")
            return 1

        scans = UserScanRepository(db)
        existing_request_ids = {
            scan.request_id for scan in scans.list_by_user(owner.id) if scan.request_id
        }

        store = _create_family_tree_store()
        extractor = FamilyExtractor()

        imported_with_tree = 0
        imported_text_only = 0
        skipped_draft = 0
        skipped_dup = 0

        for record in records:
            doc_id = record.get("doc_id") or "unknown"
            request_id = f"{REQUEST_ID_PREFIX}{doc_id}"

            if request_id in existing_request_ids:
                print(f"[SKIP đã import] {doc_id}")
                skipped_dup += 1
                continue

            text = _best_text(record)
            if not text:
                note = (record.get("ghi_chu") or "")[:80]
                print(f"[SKIP draft — chưa có text] {doc_id}: {note}")
                skipped_draft += 1
                continue

            title = _title(record)
            if args.dry_run:
                print(f"[DRY-RUN] {doc_id} -> title={title!r}, {len(text)} ký tự")
                continue

            scan = scans.create(
                user_id=owner.id,
                title=title,
                file_name=doc_id,
                file_type="hannom-corpus",
                page_count=max(1, len(record.get("pages") or [])),
                source_text=text,
            )
            scans.update(scan, ocr_status=OcrStatus.COMPLETED, request_id=request_id)

            extraction = extractor.parse(text)
            balkan_nodes, gemini_err = normalize_balkan_nodes(text, extraction)

            if balkan_nodes:
                tree = store.create_tree(
                    name=title,
                    description=record.get("dia_danh") or None,
                    nodes=balkan_nodes,
                    has_source_document=True,
                    has_hannom_text=bool(record.get("co_ban_han")),
                    user_id=owner.id,
                    is_public=True,
                )
                scans.update(scan, tree_status=TreeStatus.CREATED, family_tree_id=tree["id"])
                print(f"[OK] {doc_id} -> scan#{scan.id}, tree {tree['id']} ({len(balkan_nodes)} người)")
                imported_with_tree += 1
            else:
                print(f"[TEXT-ONLY] {doc_id} -> scan#{scan.id}, chưa tạo được cây: {gemini_err}")
                imported_text_only += 1

        print(
            "\nTổng kết — "
            f"có cây: {imported_with_tree}, chỉ có text/scan (chưa có cây): {imported_text_only}, "
            f"bỏ qua (draft/chưa có text): {skipped_draft}, bỏ qua (đã import trước): {skipped_dup}, "
            f"tổng record đọc được: {len(records)}"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
