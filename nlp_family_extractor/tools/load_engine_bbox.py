"""Nạp khung chữ của MỘT engine OCR (vd. Kim Hán Nôm Lab) vào `gia_pha_page_content.ocr_bbox_engines`.

Đầu vào: file JSON từ research/hannom-bilingual-dataset/scripts/export_engine_bbox.py
  {"schema": 1, "engine": "kim_hannom_lab",
   "books": {doc_id: {page_number: {"image_size", "boxes": [{order, bbox_xyxy, han, confidence}]}}}}

Khác load_page_bbox.py: KHÔNG đụng `ocr_bbox` (khung Paddle có sẵn) — chỉ thêm/cập nhật
khoá `<engine>` trong `ocr_bbox_engines`, giữ nguyên các engine khác. Ghi vào MỌI version
đã có nội dung cho trang đó; không tạo version/dòng nội dung mới, không đụng chữ/phiên âm/dịch.
Bộ khớp theo UserScan.request_id = "hannom-corpus:<doc_id>". Idempotent: khung đã giống thì bỏ qua.

    python3 tools/load_engine_bbox.py /tmp/kim_bbox.json                    # xem trước (mặc định)
    python3 tools/load_engine_bbox.py /tmp/kim_bbox.json --doc nom-147      # chỉ 1 bộ
    python3 tools/load_engine_bbox.py /tmp/kim_bbox.json --write            # ghi DB
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Any, Dict, Optional, Sequence

ROOT = Path(__file__).resolve().parents[1]  # nlp_family_extractor/
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.workspace.repository import GiaPhaPageRepository, GiaPhaVersionRepository  # noqa: E402

REQUEST_ID_PREFIX = "hannom-corpus:"
DEFAULT_ENGINE = "kim_hannom_lab"


def apply_book_engine_bbox(
    *,
    scan_id: int,
    engine: str,
    pages: Dict[str, Dict[str, Any]],
    pages_repo: GiaPhaPageRepository,
    versions_repo: GiaPhaVersionRepository,
    write: bool,
) -> Dict[str, int]:
    """Ghi khung của `engine` cho 1 bộ. Trả về {pages, rows_changed, missing_pages}.

    `pages` là {page_number: {"boxes": [...]}}; trang thiếu khung bị bỏ qua (không xoá khung đã có).
    """
    by_number = {p.page_number: p for p in pages_repo.list_by_scan(scan_id, include_deleted=True)}
    wanted = {
        by_number[int(n)].id: entry["boxes"] for n, entry in pages.items() if int(n) in by_number and entry.get("boxes")
    }
    changed = 0
    for version in versions_repo.list_by_scan(scan_id):
        for content in pages_repo.list_content_for_version(version.id):
            boxes = wanted.get(content.page_id)
            if boxes is None or (content.ocr_bbox_engines or {}).get(engine) == boxes:
                continue
            changed += 1
            if write:
                pages_repo.upsert_content(
                    version_id=version.id, page_id=content.page_id, ocr_bbox_engine=(engine, boxes)
                )
    return {
        "pages": len(wanted),
        "rows_changed": changed,
        "missing_pages": sum(1 for n in pages if int(n) not in by_number),
    }


def main(argv: Optional[Sequence[str]] = None) -> int:
    from app.auth.user_repository import UserRepository
    from app.database import database_enabled, init_database, session_scope
    from app.workspace.repository import UserScanRepository

    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("file", type=Path)
    ap.add_argument("--engine", default=None, help=f"tên khoá engine (mặc định: lấy từ file, hoặc {DEFAULT_ENGINE})")
    ap.add_argument("--doc", action="append", default=[], help="chỉ các doc_id này")
    ap.add_argument("--write", action="store_true", help="Ghi DB (mặc định chỉ in ra)")
    ap.add_argument("--owner-email", default=os.environ.get("ADMIN_EMAIL", "admin@giapha.com"))
    args = ap.parse_args(argv)

    data = json.loads(args.file.read_text(encoding="utf-8"))
    if data.get("schema") != 1:
        print("File không đúng schema 1 — dừng.")
        return 1
    engine = args.engine or data.get("engine") or DEFAULT_ENGINE
    init_database()
    if not database_enabled():
        print("Không kết nối được MySQL — dừng.")
        return 1
    with session_scope() as db:
        owner = UserRepository(db).get_by_email(args.owner_email)
        if owner is None:
            print(f"Không có user {args.owner_email} — dừng.")
            return 1
        scans = {s.request_id: s for s in UserScanRepository(db).list_by_user(owner.id, include_deleted=True) if s.request_id}
        pages_repo, versions_repo = GiaPhaPageRepository(db), GiaPhaVersionRepository(db)
        tag = "GHI" if args.write else "XEM TRƯỚC"
        for doc_id, pages in data["books"].items():
            if args.doc and doc_id not in args.doc:
                continue
            scan = scans.get(f"{REQUEST_ID_PREFIX}{doc_id}")
            if scan is None:
                print(f"[{tag}] {doc_id}: chưa import lên web — bỏ")
                continue
            stats = apply_book_engine_bbox(
                scan_id=scan.id,
                engine=engine,
                pages=pages,
                pages_repo=pages_repo,
                versions_repo=versions_repo,
                write=args.write,
            )
            print(f"[{tag}] {doc_id} -> scan#{scan.id} engine={engine}: {stats}")
        if not args.write:
            db.rollback()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
