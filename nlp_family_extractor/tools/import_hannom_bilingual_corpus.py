#!/usr/bin/env python3
"""Import dữ liệu Hán Nôm đã xử lý (repo `hannom-bilingual-dataset`, dữ liệu
thật — xem `research/hannom-bilingual-dataset/scripts/_repo_paths.py` cho quy
ước `HANNOM_DATA_ROOT`) vào hệ quản lý gia phả thật của app này (`UserScan` +
`FamilyTree`, MySQL) — thay cho việc 2 hệ thống này đang hoàn toàn tách biệt.

Mỗi record trở thành 1 UserScan (title/text đã OCR+dịch sẵn, ocr_status=
completed) thuộc về 1 tài khoản cố định (--owner-email) — lưu đủ 3 lớp:
`source_text` (dịch nghĩa Quốc ngữ, dùng để trích xuất quan hệ), `hannom_text`
(OCR Hán-Nôm đã vote, L1), `transliteration_text` (phiên âm Hán-Việt, L2), và
`ocr_vote_meta` (JSON: vote_method/engines/uncertain_rate/uncertain_spans/
structural_diffs theo từng trang — bằng chứng "đồng thuận đến đâu, chỗ nào
chưa chắc" từ scripts/vote_ocr.py, không chỉ giữ mỗi kết quả cuối). Nếu trích
xuất được quan hệ nhân vật (cần GOOGLE_API_KEY — lưu qua Admin › Developer ›
Cấu hình, hoặc biến môi trường, xem app/config.py:get_google_api_key), tạo
thêm 1 FamilyTree công khai (is_public=True, xuất hiện ở "Gia phả mẫu"/
`/gia-pha`) và gắn family_tree_id + tree_status=created vào scan. KHÔNG có
GOOGLE_API_KEY: vẫn import scan/text (trung thực, không giả vờ có cây) —
tree_status giữ NONE, in rõ lý do.

KHÔNG xử lý ảnh gốc — chạy riêng
`tools/attach_hannom_corpus_images.py` sau khi đã upload ảnh/file gốc lên
MinIO (xem docstring file đó cho quy ước thư mục staging).

Idempotent: mỗi lần chạy lại, record đã import trước (khớp theo doc_id, lưu
trong UserScan.request_id với prefix "hannom-corpus:") sẽ được bỏ qua, không
tạo trùng.

Chạy (từ nlp_family_extractor/, cần MYSQL_HOST/MYSQL_USER/MYSQL_PASSWORD
trong env, giống khi chạy `uvicorn api:app`; GOOGLE_API_KEY lấy từ DB nếu đã
cấu hình qua Admin › Developer › Cấu hình, không cần set lại ở đây):

    python3 tools/import_hannom_bilingual_corpus.py --dry-run   # xem trước
    python3 tools/import_hannom_bilingual_corpus.py             # import thật
    python3 tools/import_hannom_bilingual_corpus.py --backfill --dry-run
        # bộ đã import trước: xem sẽ ghi mã định danh đã chốt + tạo trang/version
    python3 tools/import_hannom_bilingual_corpus.py --refresh-vote --dry-run
        # corpus đã vote lại theo từng chữ (schema 2): xem sẽ tạo version mới
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
from app.workspace.ma_dinh_danh import corpus_identifier_fields  # noqa: E402
from app.workspace.models import OcrStatus, TreeStatus  # noqa: E402
from app.workspace.repository import (  # noqa: E402
    GiaPhaPageRepository,
    GiaPhaVersionRepository,
    UserScanRepository,
)

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


def _join_pages(record: Dict[str, Any], get_field) -> Optional[str]:
    """Ghép 1 lớp cụ thể (vd l1_ocr.voted_text, l2_phien_am) qua toàn bộ
    trang, theo đúng thứ tự — trả None nếu không trang nào có lớp này."""
    pages = record.get("pages") or []
    parts: List[str] = []
    for page in pages:
        value = get_field(page)
        if value:
            parts.append(value.strip())
    joined = "\n\n".join(p for p in parts if p)
    return joined or None


def _hannom_text(record: Dict[str, Any]) -> Optional[str]:
    """Văn bản Hán-Nôm gốc (OCR đã vote, L1) — không phải bản dịch/phiên âm."""
    def _get(page: Dict[str, Any]) -> Optional[str]:
        l1 = page.get("l1_ocr")
        return l1.get("voted_text") if isinstance(l1, dict) else None

    return _join_pages(record, _get)


def _transliteration_text(record: Dict[str, Any]) -> Optional[str]:
    """Phiên âm Hán-Việt (L2) — riêng biệt với dịch nghĩa Quốc ngữ (L3)."""
    return _join_pages(record, lambda page: page.get("l2_phien_am"))


_V1_VOTE_KEYS = ("vote_method", "engines", "uncertain_rate", "uncertain_spans", "structural_diffs")


def _page_vote_meta(l1: Any) -> Optional[Dict[str, Any]]:
    """ocr_vote_meta của 1 trang từ `l1_ocr` của record.

    - schema 2 (vote theo từng chữ, research/.../revote_char_records.py): mọi
      trường meta + `lines` (= voted_text tách dòng, giao diện cần để tô từng chữ).
    - schema 1 (vote theo dòng, cũ): 5 trường như trước; None nếu không có gì.
    voted_text không nằm trong meta — lưu riêng ở hannom_text."""
    if not isinstance(l1, dict):
        return None
    if l1.get("schema_version") == 2:
        meta = {k: v for k, v in l1.items() if k != "voted_text"}
        meta["lines"] = (l1.get("voted_text") or "").split("\n") if l1.get("voted_text") else []
        return meta
    if not any(l1.get(k) not in (None, [], {}) for k in ("vote_method", "engines", "uncertain_rate", "uncertain_spans")):
        return None
    return {k: l1.get(k) for k in _V1_VOTE_KEYS}


def _vote_meta(record: Dict[str, Any]) -> Optional[List[Dict[str, Any]]]:
    """Metadata vote OCR theo trang — vote_method/engines/uncertain_rate/
    uncertain_spans/structural_diffs từ scripts/vote_ocr.py, KHÔNG kèm
    voted_text (đã lưu riêng ở hannom_text). Giữ lại để soát lỗi/QA: biết
    được đoạn nào các engine OCR bất đồng thay vì chỉ thấy kết quả cuối."""
    pages = record.get("pages") or []
    meta: List[Dict[str, Any]] = []
    for page in pages:
        l1 = page.get("l1_ocr")
        if not isinstance(l1, dict):
            continue
        if l1.get("schema_version") == 2:
            meta.append({"page_id": page.get("page_id"), **(_page_vote_meta(l1) or {})})
            continue
        entry = {"page_id": page.get("page_id"), **{k: l1.get(k) for k in _V1_VOTE_KEYS}}
        # Chỉ giữ trang có ít nhất 1 field thật (đừng nhét toàn None vào JSON).
        if any(v not in (None, [], {}) for k, v in entry.items() if k != "page_id"):
            meta.append(entry)
    return meta or None


def _create_pages_version_and_content(
    *,
    pages_repo: GiaPhaPageRepository,
    versions_repo: GiaPhaVersionRepository,
    user_scan_id: int,
    record: Dict[str, Any],
    owner_id: int,
) -> None:
    """Tạo gia_pha_page (1/trang, image_file_key = l0_image gốc, ảnh thật
    upload sau qua attach_hannom_corpus_images.py) + 1 gia_pha_version (v1,
    is_current=true, engine="corpus_import") + gia_pha_page_content cho từng
    trang (l1_ocr/l2_phien_am/l3_dich_nghia) — thay vì chỉ ghi blob phẳng, để
    21+ bản ghi import có sẵn cấu trúc trang/version ngay từ đầu (mục E của
    plan hợp nhất Gia phả)."""
    pages = record.get("pages") or []
    if not pages:
        return
    version = versions_repo.create_version(
        user_scan_id=user_scan_id,
        ocr_engines=["corpus_import"],
        created_by=owner_id,
        note="Import từ hannom-bilingual-dataset",
        make_current=True,
    )
    for index, page in enumerate(pages, start=1):
        l1 = page.get("l1_ocr")
        l1 = l1 if isinstance(l1, dict) else {}
        gia_pha_page = pages_repo.create_page(
            user_scan_id=user_scan_id,
            page_number=index,
            image_file_key=page.get("l0_image"),
        )
        vote_meta = _page_vote_meta(l1)
        pages_repo.upsert_content(
            version_id=version.id,
            page_id=gia_pha_page.id,
            hannom_text=l1.get("voted_text"),
            transliteration_text=page.get("l2_phien_am"),
            translation_text=page.get("l3_dich_nghia"),
            ocr_vote_meta=vote_meta,
        )
    # Cache phẳng (UserScan.hannom_text/transliteration_text/source_text) đã
    # được ghi trực tiếp từ _hannom_text()/_transliteration_text()/_best_text()
    # khi tạo scan ở main() — không cần sync lại ở đây.


def backfill_structure(
    *,
    scan: Any,
    record: Dict[str, Any],
    scans: UserScanRepository,
    pages_repo: GiaPhaPageRepository,
    versions_repo: GiaPhaVersionRepository,
    owner_id: int,
    dry_run: bool,
) -> List[str]:
    """--backfill cho scan đã import trước: (1) mã định danh + thông tin đi
    kèm ĐÃ CHỐT ở catalogue (chép nguyên văn), (2) trang + version v1 nếu scan
    chưa có (bản ghi import trước khi có mô hình trang/version). Idempotent:
    chỉ ghi phần còn thiếu/khác. Trả về danh sách việc đã (hoặc sẽ) làm."""
    actions: List[str] = []
    fields, warnings = corpus_identifier_fields(record)
    actions += [f"CẢNH BÁO: {w}" for w in warnings]
    changed = {k: v for k, v in fields.items() if getattr(scan, k, None) != v}
    if changed:
        actions.append("mã định danh/thông tin: " + ", ".join(sorted(changed)))
        if not dry_run:
            scans.set_corpus_identifiers(scan, changed)
    if not pages_repo.list_by_scan(scan.id) and record.get("pages"):
        actions.append(f"tạo {len(record['pages'])} trang + version v1")
        if not dry_run:
            _create_pages_version_and_content(
                pages_repo=pages_repo,
                versions_repo=versions_repo,
                user_scan_id=scan.id,
                record=record,
                owner_id=owner_id,
            )
    return actions


def refresh_text(
    *,
    scan: Any,
    record: Dict[str, Any],
    scans: UserScanRepository,
    pages_repo: GiaPhaPageRepository,
    versions_repo: GiaPhaVersionRepository,
    owner_id: int,
    dry_run: bool,
) -> List[str]:
    """--refresh-text: corpus có phiên âm (l2)/dịch nghĩa (l3) mới hơn version
    hiện tại của scan → tạo version MỚI (cha = version hiện tại, v1 giữ nguyên),
    chỉ thay các trang có giá trị corpus khác rỗng và khác bản hiện tại, đặt làm
    version hiện tại + đồng bộ cache phẳng trên UserScan (trang đọc tài liệu).
    KHÔNG đưa `pairs` của corpus vào (dạng {han, viet} nháp LLM, thiếu phiên
    âm — không dùng làm dữ liệu train). Không có gì khác → không tạo version."""
    current = versions_repo.get_current(scan.id)
    pages = {p.page_number: p for p in pages_repo.list_by_scan(scan.id)}
    if current is None or not pages:
        return []
    contents = {c.page_id: c for c in pages_repo.list_content_for_version(current.id)}
    updates: Dict[int, Dict[str, str]] = {}
    for number, page in enumerate(record.get("pages") or [], start=1):
        if number not in pages or not isinstance(page, dict):
            continue
        base = contents.get(pages[number].id)
        for src, dst in (("l2_phien_am", "transliteration_text"), ("l3_dich_nghia", "translation_text")):
            value = page.get(src)
            if isinstance(value, str) and value.strip() and value != getattr(base, dst, None):
                updates.setdefault(number, {})[dst] = value
    if not updates:
        return []
    n_l2 = sum(1 for u in updates.values() if "transliteration_text" in u)
    n_l3 = sum(1 for u in updates.values() if "translation_text" in u)
    action = f"version mới (hiện tại) cập nhật {len(updates)} trang: phiên âm {n_l2}, dịch nghĩa {n_l3}"
    if dry_run:
        return [action]
    version = versions_repo.create_derived_version(
        user_scan_id=scan.id,
        parent_version_id=current.id,
        source="corpus",
        review_status=None,
        note=f"Cập nhật phiên âm/dịch nghĩa từ hannom-bilingual-dataset ({len(updates)} trang)",
        created_by=owner_id,
        text_step_status="done",
    )
    for number, fields in updates.items():
        pages_repo.upsert_content(version_id=version.id, page_id=pages[number].id, **fields)
    versions_repo.set_current(scan.id, version.id)
    pages_repo.sync_flat_cache(scans, scan.id, version.id)  # cùng session — commit cả set_current
    return [action]


def refresh_vote(
    *,
    scan: Any,
    record: Dict[str, Any],
    scans: UserScanRepository,
    pages_repo: GiaPhaPageRepository,
    versions_repo: GiaPhaVersionRepository,
    owner_id: int,
    dry_run: bool,
) -> List[str]:
    """--refresh-vote: corpus đã vote lại theo TỪNG CHỮ (l1_ocr schema 2) →
    version MỚI (cha = version hiện tại, giữ nguyên), chỉ thay hannom_text +
    ocr_vote_meta của các trang khác bản hiện tại; phiên âm/dịch nghĩa giữ
    nguyên (trang có `downstream_stale` có thể lệch — không tự chạy lại vì tốn
    tiền). Đặt làm version hiện tại + đồng bộ cache phẳng. Không có gì khác →
    không tạo version (idempotent)."""
    current = versions_repo.get_current(scan.id)
    pages = {p.page_number: p for p in pages_repo.list_by_scan(scan.id)}
    if current is None or not pages:
        return []
    contents = {c.page_id: c for c in pages_repo.list_content_for_version(current.id)}
    updates: Dict[int, Dict[str, Any]] = {}
    stale = 0
    for number, page in enumerate(record.get("pages") or [], start=1):
        l1 = page.get("l1_ocr") if isinstance(page, dict) else None
        if number not in pages or not isinstance(l1, dict) or l1.get("schema_version") != 2:
            continue
        base = contents.get(pages[number].id)
        fields = {"hannom_text": l1.get("voted_text"), "ocr_vote_meta": _page_vote_meta(l1)}
        if any(fields[k] != getattr(base, k, None) for k in fields):
            updates[number] = fields
            stale += bool(l1.get("downstream_stale"))
    if not updates:
        return []
    action = f"version mới (hiện tại) vote theo từng chữ: {len(updates)} trang, {stale} trang phiên âm/dịch có thể lệch"
    if dry_run:
        return [action]
    version = versions_repo.create_derived_version(
        user_scan_id=scan.id,
        parent_version_id=current.id,
        source="corpus",
        review_status=None,
        note=f"Vote OCR theo từng chữ (schema 2) từ hannom-bilingual-dataset ({len(updates)} trang)",
        created_by=owner_id,
        text_step_status="done",
    )
    for number, fields in updates.items():
        pages_repo.upsert_content(version_id=version.id, page_id=pages[number].id, **fields)
    versions_repo.set_current(scan.id, version.id)
    # Danh sách vote theo trang trên UserScan (trang đọc tài liệu mở lại bộ) —
    # sync_flat_cache không đụng tới trường này.
    scans.update(scan, ocr_vote_meta=_vote_meta(record))
    pages_repo.sync_flat_cache(scans, scan.id, version.id)
    return [action]


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
    parser.add_argument(
        "--refresh-text",
        action="store_true",
        help="Với bộ đã import: corpus có phiên âm/dịch nghĩa mới → tạo version mới (đặt làm hiện tại), giữ version cũ",
    )
    parser.add_argument(
        "--refresh-vote",
        action="store_true",
        help="Với bộ đã import: corpus đã vote lại theo từng chữ (schema 2) → tạo version mới (đặt làm hiện tại), giữ version cũ",
    )
    parser.add_argument(
        "--backfill",
        action="store_true",
        help="Với bộ đã import trước: ghi mã định danh đã chốt + tạo trang/version v1 nếu còn thiếu",
    )
    parser.add_argument(
        "--include-draft",
        action="store_true",
        help="Cho phép import bộ chưa có text (OCR/phiên âm/dịch) với ocr_status=PENDING (mặc định: bỏ qua)",
    )
    parser.add_argument(
        "--no-tree",
        action="store_true",
        help="Bỏ qua tạo FamilyTree (không gọi Gemini) — set tree_status=NONE (mặc định: tạo cây nếu có text)",
    )
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
        pages_repo = GiaPhaPageRepository(db)
        versions_repo = GiaPhaVersionRepository(db)
        existing_by_request_id = {
            scan.request_id: scan for scan in scans.list_by_user(owner.id) if scan.request_id
        }

        store = _create_family_tree_store()
        extractor = FamilyExtractor()

        imported_with_tree = 0
        imported_text_only = 0
        skipped_draft = 0
        skipped_dup = 0
        backfilled = 0

        for record in records:
            doc_id = record.get("doc_id") or "unknown"
            request_id = f"{REQUEST_ID_PREFIX}{doc_id}"

            existing_scan = existing_by_request_id.get(request_id)
            if existing_scan is not None:
                # Đã import trước — không tạo trùng, nhưng backfill từng field
                # còn thiếu độc lập (vd chạy bằng script bản cũ trước khi có
                # hannom_text/transliteration_text, hoặc trước khi có
                # ocr_vote_meta — không phải all-or-nothing, kẻo 1 field mới
                # thêm sau bị bỏ sót cho record đã backfill field khác rồi).
                backfill_kwargs: Dict[str, Any] = {}
                if not existing_scan.hannom_text:
                    hannom = _hannom_text(record)
                    if hannom:
                        backfill_kwargs["hannom_text"] = hannom
                if not existing_scan.transliteration_text:
                    translit = _transliteration_text(record)
                    if translit:
                        backfill_kwargs["transliteration_text"] = translit
                if not existing_scan.ocr_vote_meta:
                    vote_meta = _vote_meta(record)
                    if vote_meta:
                        backfill_kwargs["ocr_vote_meta"] = vote_meta
                actions = []
                if backfill_kwargs:
                    actions.append("text: " + ", ".join(backfill_kwargs))
                    if not args.dry_run:
                        scans.update(existing_scan, **backfill_kwargs)
                if args.backfill:
                    actions += backfill_structure(
                        scan=existing_scan,
                        record=record,
                        scans=scans,
                        pages_repo=pages_repo,
                        versions_repo=versions_repo,
                        owner_id=owner.id,
                        dry_run=args.dry_run,
                    )
                if args.refresh_text:
                    actions += refresh_text(
                        scan=existing_scan,
                        record=record,
                        scans=scans,
                        pages_repo=pages_repo,
                        versions_repo=versions_repo,
                        owner_id=owner.id,
                        dry_run=args.dry_run,
                    )
                if args.refresh_vote:
                    actions += refresh_vote(
                        scan=existing_scan,
                        record=record,
                        scans=scans,
                        pages_repo=pages_repo,
                        versions_repo=versions_repo,
                        owner_id=owner.id,
                        dry_run=args.dry_run,
                    )
                if actions:
                    tag = "DRY-RUN BACKFILL" if args.dry_run else "BACKFILL"
                    print(f"[{tag}] {doc_id} -> scan#{existing_scan.id}: " + "; ".join(actions))
                    backfilled += 1
                    continue
                print(f"[SKIP đã import] {doc_id}")
                skipped_dup += 1
                continue

            text = _best_text(record)
            is_draft = not text
            if is_draft and not args.include_draft:
                note = (record.get("ghi_chu") or "")[:80]
                print(f"[SKIP draft — chưa có text] {doc_id}: {note}")
                skipped_draft += 1
                continue

            title = _title(record)
            if args.dry_run:
                status_label = "DRAFT" if is_draft else "OK"
                text_size = f"{len(text)} ký tự" if text else "—"
                print(f"[DRY-RUN {status_label}] {doc_id} -> title={title!r}, {text_size}")
                continue

            scan = scans.create(
                user_id=owner.id,
                title=title,
                file_name=doc_id,
                file_type="hannom-corpus",
                page_count=max(1, len(record.get("pages") or [])),
                source_text=text,
                hannom_text=_hannom_text(record),
                transliteration_text=_transliteration_text(record),
                ocr_vote_meta=_vote_meta(record),
            )
            ocr_st = OcrStatus.PENDING if is_draft else OcrStatus.COMPLETED
            scans.update(scan, ocr_status=ocr_st, request_id=request_id)
            identifier_fields, identifier_warnings = corpus_identifier_fields(record)
            for warning in identifier_warnings:
                print(f"[CẢNH BÁO] {doc_id}: {warning}")
            if identifier_fields:
                scans.set_corpus_identifiers(scan, identifier_fields)
            if text:
                _create_pages_version_and_content(
                    pages_repo=pages_repo,
                    versions_repo=versions_repo,
                    user_scan_id=scan.id,
                    record=record,
                    owner_id=owner.id,
                )

            if args.no_tree:
                print(f"[DRAFT] {doc_id} -> scan#{scan.id}, tree_status=NONE (--no-tree)")
                imported_text_only += 1
            elif text:
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
            else:
                print(f"[DRAFT] {doc_id} -> scan#{scan.id} (chưa có text)")
                imported_text_only += 1

        print(
            "\nTổng kết — "
            f"có cây: {imported_with_tree}, chỉ có text/scan (chưa có cây): {imported_text_only}, "
            f"bỏ qua (draft/chưa có text): {skipped_draft}, bỏ qua (đã import trước): {skipped_dup}, "
            f"backfill: {backfilled}, tổng record đọc được: {len(records)}"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
