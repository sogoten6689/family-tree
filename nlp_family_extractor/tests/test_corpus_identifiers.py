import importlib.util
import unittest
from pathlib import Path
from unittest import mock

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.dialects.mysql import LONGTEXT
from sqlalchemy.ext.compiler import compiles
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

import api
from app.auth.dependencies import get_current_user, get_optional_current_user
from app.auth.models import User, UserRole
from app.database import Base, get_db
from app.workspace import models
from app.workspace.ma_dinh_danh import corpus_identifier_fields
from app.workspace.repository import GiaPhaPageRepository, GiaPhaVersionRepository, UserScanRepository
from app.workspace.router import require_workspace_database


@compiles(LONGTEXT, "sqlite")
def _longtext_as_sqlite_text(_type, _compiler, **_kw) -> str:
    return "TEXT"


_spec = importlib.util.spec_from_file_location(
    "import_corpus", Path(__file__).resolve().parents[1] / "tools" / "import_hannom_bilingual_corpus.py"
)
import_corpus = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(import_corpus)

RECORD = {
    "doc_id": "pdf-phan-gia-cong-pha",
    "ma_dinh_danh": "F-B-PN-GiaThien-001-1930",
    "quy_mo": "Tộc phả",
    "hinh_thuc": "Bộ",
    "ho": "Phan",
    "dia_danh": "Gia Thiện (đại tôn) / Hữu Phương (tiểu tôn), xã Thạch Châu, huyện Thạch Hà, tỉnh Hà Tĩnh " * 2,
    "nien_dai": "Bản gốc: không trước 1930 (Bảo Đại 5) · Bản dịch in: 2006",
    "pages": [
        {"page_id": "p1", "l0_image": "a.jpg", "l1_ocr": {"voted_text": "乾坤"}, "l2_phien_am": "Càn khôn", "l3_dich_nghia": "Trời đất"},
        {"page_id": "p2", "l0_image": "b.jpg", "l1_ocr": {"voted_text": "家譜"}, "l2_phien_am": "Gia phả", "l3_dich_nghia": "Phả hệ"},
    ],
}


class CorpusIdentifierFieldsTest(unittest.TestCase):
    def test_copies_confirmed_code_and_takes_year_from_code(self) -> None:
        fields, warnings = corpus_identifier_fields(RECORD)
        self.assertEqual(warnings, [])
        self.assertEqual(fields["ma_dinh_danh"], "F-B-PN-GiaThien-001-1930")
        self.assertEqual(fields["ma_dinh_danh_nguon"], "catalogue")
        self.assertEqual(fields["nam_soan_goc"], 1930)  # từ mã, không đọc văn "2006"
        self.assertEqual(fields["ho_toc"], "Phan")
        self.assertTrue(fields["nien_dai_mo_ta"].startswith("Bản gốc"))
        self.assertLessEqual(len(fields["dia_danh"]), 512)

    def test_malformed_code_is_not_written(self) -> None:
        fields, warnings = corpus_identifier_fields({**RECORD, "ma_dinh_danh": "F-B-PN-GiaThien-1-1930"})
        self.assertNotIn("ma_dinh_danh", fields)
        self.assertNotIn("nam_soan_goc", fields)
        self.assertEqual(len(warnings), 1)

    def test_annotated_classification_is_skipped_not_stored(self) -> None:
        # Giá trị thật gây lỗi backfill production 02/10/2026 (nom-207, nom-84).
        record = {
            **RECORD,
            "quy_mo": "Tộc phả (theo tên gọi, chưa đọc để xác nhận)",
            "hinh_thuc": "Ký (khớp tên gọi + nội dung, đọc trực tiếp trang 1)",
            "ho": "X" * 70,
        }
        fields, warnings = corpus_identifier_fields(record)
        self.assertNotIn("quy_mo", fields)
        self.assertNotIn("hinh_thuc", fields)
        self.assertNotIn("ho_toc", fields)
        self.assertEqual(len(warnings), 3)
        self.assertEqual(fields["ma_dinh_danh"], "F-B-PN-GiaThien-001-1930")  # mã đã chốt vẫn giữ

    def test_record_without_code_keeps_other_fields_only(self) -> None:
        fields, _ = corpus_identifier_fields({k: v for k, v in RECORD.items() if k != "ma_dinh_danh"})
        self.assertNotIn("ma_dinh_danh", fields)
        self.assertEqual(fields["quy_mo"], "Tộc phả")


class _Db:
    def setUp(self) -> None:
        self.engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
        Base.metadata.create_all(
            self.engine,
            tables=[
                User.__table__,
                models.UserScan.__table__,
                models.GiaPhaPage.__table__,
                models.GiaPhaVersion.__table__,
                models.GiaPhaVersionStep.__table__,
                models.GiaPhaPageContent.__table__,
            ],
        )
        self.db = Session(self.engine)
        self.owner = User(email="a@t.l", full_name="A", password_hash="x", role=UserRole.ADMIN)
        self.db.add(self.owner)
        self.db.commit()
        self.scans = UserScanRepository(self.db)

    def tearDown(self) -> None:
        self.db.close()

    def new_scan(self, **kw):
        return self.scans.create(user_id=self.owner.id, title="GP", file_name="x", file_type="hannom-corpus", **kw)


class BackfillTest(_Db, unittest.TestCase):
    def _backfill(self, scan, dry_run):
        return import_corpus.backfill_structure(
            scan=scan,
            record=RECORD,
            scans=self.scans,
            pages_repo=GiaPhaPageRepository(self.db),
            versions_repo=GiaPhaVersionRepository(self.db),
            owner_id=self.owner.id,
            dry_run=dry_run,
        )

    def test_dry_run_reports_but_writes_nothing(self) -> None:
        scan = self.new_scan()
        actions = self._backfill(scan, dry_run=True)
        self.assertTrue(any("mã định danh" in a for a in actions))
        self.assertTrue(any("tạo 2 trang" in a for a in actions))
        self.db.refresh(scan)
        self.assertIsNone(scan.ma_dinh_danh)
        self.assertEqual(GiaPhaPageRepository(self.db).list_by_scan(scan.id), [])

    def test_backfill_writes_code_pages_and_current_version_then_is_idempotent(self) -> None:
        scan = self.new_scan()
        self._backfill(scan, dry_run=False)
        self.db.refresh(scan)
        self.assertEqual(scan.ma_dinh_danh, "F-B-PN-GiaThien-001-1930")
        pages = GiaPhaPageRepository(self.db).list_by_scan(scan.id)
        self.assertEqual([p.page_number for p in pages], [1, 2])
        current = GiaPhaVersionRepository(self.db).get_current(scan.id)
        self.assertIsNotNone(current)
        contents = GiaPhaPageRepository(self.db).list_content_for_version(current.id)
        self.assertEqual(sorted(c.transliteration_text for c in contents), ["Càn khôn", "Gia phả"])
        self.assertEqual(self._backfill(scan, dry_run=False), [])  # chạy lại: không còn gì để làm
        self.assertEqual(len(GiaPhaVersionRepository(self.db).list_by_scan(scan.id)), 1)


class TreeListShowsSourceCodeTest(_Db, unittest.TestCase):
    def setUp(self) -> None:
        super().setUp()
        scan = self.new_scan()
        self.scans.set_corpus_identifiers(scan, {"ma_dinh_danh": "F-B-PN-GiaThien-001-1930"})
        self.scans.update(scan, family_tree_id="tree-1")
        self.scan_id = scan.id
        trees = [
            {"id": "tree-1", "name": "Phan gia", "is_public": True, "updated_at": "2026-10-02", "node_count": 3},
            {"id": "tree-2", "name": "Không nguồn", "is_public": True, "updated_at": "2026-10-02", "node_count": 1},
        ]
        store = mock.Mock(list_trees=mock.Mock(return_value=trees), list_public_trees=mock.Mock(return_value=trees))
        self.patch = mock.patch.object(api, "_family_tree_store", store)
        self.patch.start()
        api.app.dependency_overrides[get_db] = lambda: self.db
        api.app.dependency_overrides[require_workspace_database] = lambda: None
        self.client = TestClient(api.app)

    def tearDown(self) -> None:
        self.patch.stop()
        api.app.dependency_overrides.clear()
        super().tearDown()

    def _items(self):
        return {i["tree_id"]: i for i in self.client.get("/api/gia-pha").json()["items"] if i["tree_id"]}

    def test_admin_sees_code_and_scan_for_built_tree(self) -> None:
        api.app.dependency_overrides[get_optional_current_user] = lambda: self.owner
        api.app.dependency_overrides[get_current_user] = lambda: self.owner
        items = self._items()
        self.assertEqual(items["tree-1"]["id"], "F-B-PN-GiaThien-001-1930")
        self.assertFalse(items["tree-1"]["ma_dinh_danh_pending"])
        self.assertEqual(items["tree-1"]["scan_id"], self.scan_id)
        self.assertEqual(items["tree-2"]["id"], "tree-2")
        self.assertTrue(items["tree-2"]["ma_dinh_danh_pending"])  # trước đây ghi sai False

    def test_guest_sees_code_but_not_private_scan_id(self) -> None:
        api.app.dependency_overrides[get_optional_current_user] = lambda: None
        items = self._items()
        self.assertEqual(items["tree-1"]["id"], "F-B-PN-GiaThien-001-1930")
        self.assertIsNone(items["tree-1"]["scan_id"])


if __name__ == "__main__":
    unittest.main()

class RefreshTextTest(_Db, unittest.TestCase):
    def _run(self, scan, record, dry_run=False):
        return import_corpus.refresh_text(
            scan=scan,
            record=record,
            scans=self.scans,
            pages_repo=GiaPhaPageRepository(self.db),
            versions_repo=GiaPhaVersionRepository(self.db),
            owner_id=self.owner.id,
            dry_run=dry_run,
        )

    def _imported_scan(self):
        scan = self.new_scan()
        import_corpus.backfill_structure(
            scan=scan, record=RECORD, scans=self.scans, pages_repo=GiaPhaPageRepository(self.db),
            versions_repo=GiaPhaVersionRepository(self.db), owner_id=self.owner.id, dry_run=False,
        )
        return scan

    def _updated_record(self):
        pages = [dict(p) for p in RECORD["pages"]]
        pages[1]["l3_dich_nghia"] = "Phả hệ (bản dịch mới)"
        pages[0]["pairs"] = [{"han": "乾坤", "viet": "Trời đất", "align_method": "llm_draft"}]
        return {**RECORD, "pages": pages}

    def test_nothing_new_creates_nothing(self) -> None:
        scan = self._imported_scan()
        self.assertEqual(self._run(scan, RECORD), [])
        self.assertEqual(len(GiaPhaVersionRepository(self.db).list_by_scan(scan.id)), 1)

    def test_dry_run_reports_without_writing(self) -> None:
        scan = self._imported_scan()
        actions = self._run(scan, self._updated_record(), dry_run=True)
        self.assertIn("cập nhật 1 trang", actions[0])
        self.assertEqual(len(GiaPhaVersionRepository(self.db).list_by_scan(scan.id)), 1)

    def test_new_current_version_keeps_v1_and_skips_pairs(self) -> None:
        scan = self._imported_scan()
        versions = GiaPhaVersionRepository(self.db)
        v1 = versions.get_current(scan.id)
        self._run(scan, self._updated_record())
        current = versions.get_current(scan.id)
        self.assertNotEqual(current.id, v1.id)
        self.assertEqual((current.source, current.parent_version_id), ("corpus", v1.id))
        pages = GiaPhaPageRepository(self.db)
        new = {c.page_id: c for c in pages.list_content_for_version(current.id)}
        old = {c.page_id: c for c in pages.list_content_for_version(v1.id)}
        p2 = max(new)
        self.assertEqual(new[p2].translation_text, "Phả hệ (bản dịch mới)")
        self.assertEqual(old[p2].translation_text, "Phả hệ")  # v1 giữ nguyên
        self.assertEqual(new[min(new)].hannom_text, "乾坤")  # OCR giữ
        self.assertTrue(all(c.pairs is None for c in new.values()))  # không đưa pairs nháp vào
        self.db.refresh(scan)
        self.assertIn("Phả hệ (bản dịch mới)", scan.source_text)  # cache phẳng cho trang đọc
        self.assertEqual(self._run(scan, self._updated_record()), [])  # chạy lại: idempotent

    def test_empty_corpus_value_never_erases(self) -> None:
        scan = self._imported_scan()
        pages = [dict(p) for p in RECORD["pages"]]
        pages[0]["l3_dich_nghia"] = None
        pages[1]["l2_phien_am"] = "  "
        self.assertEqual(self._run(scan, {**RECORD, "pages": pages}), [])


def _v2_l1(voted_text, auto_fixed=0, stale=True):
    return {
        "voted_text": voted_text, "schema_version": 2, "vote_method": "char_majority", "backbone": "kim",
        "page_status": "ok", "thresholds": {"auto_min": 3, "suggest_min": 2},
        "stats": {"chars": len(voted_text), "auto_fixed": auto_fixed}, "review_rate": 0.0, "uncertain_rate": 0.0,
        "engines": {"kim": {"text": voted_text, "han_chars": len(voted_text), "voted": True, "excluded": None}},
        "slots": [], "downstream_stale": stale,
    }


class RefreshVoteTest(RefreshTextTest):
    def _run(self, scan, record, dry_run=False):
        return import_corpus.refresh_vote(
            scan=scan, record=record, scans=self.scans, pages_repo=GiaPhaPageRepository(self.db),
            versions_repo=GiaPhaVersionRepository(self.db), owner_id=self.owner.id, dry_run=dry_run,
        )

    def _updated_record(self):
        pages = [dict(p) for p in RECORD["pages"]]
        pages[1]["l1_ocr"] = _v2_l1("家\n譜", auto_fixed=1)
        return {**RECORD, "pages": pages}

    def test_dry_run_reports_without_writing(self) -> None:
        scan = self._imported_scan()
        actions = self._run(scan, self._updated_record(), dry_run=True)
        self.assertIn("1 trang, 1 trang phiên âm/dịch có thể lệch", actions[0])
        self.assertEqual(len(GiaPhaVersionRepository(self.db).list_by_scan(scan.id)), 1)

    def test_new_current_version_keeps_v1_and_skips_pairs(self) -> None:
        scan = self._imported_scan()
        versions, pages = GiaPhaVersionRepository(self.db), GiaPhaPageRepository(self.db)
        v1 = versions.get_current(scan.id)
        self._run(scan, self._updated_record())
        current = versions.get_current(scan.id)
        self.assertEqual((current.source, current.parent_version_id), ("corpus", v1.id))
        new = {c.page_id: c for c in pages.list_content_for_version(current.id)}
        old = {c.page_id: c for c in pages.list_content_for_version(v1.id)}
        p1, p2 = min(new), max(new)
        self.assertEqual(new[p2].hannom_text, "家\n譜")
        meta = new[p2].ocr_vote_meta
        self.assertEqual((meta["schema_version"], meta["lines"], meta["stats"]["auto_fixed"]), (2, ["家", "譜"], 1))
        self.assertNotIn("voted_text", meta)
        self.assertEqual((new[p2].translation_text, new[p2].transliteration_text), ("Phả hệ", "Gia phả"))  # giữ L2/L3
        self.assertEqual(old[p2].hannom_text, "家譜")  # version cũ giữ nguyên
        self.assertEqual(new[p1].hannom_text, "乾坤")  # trang không phải schema 2 không đổi
        self.db.refresh(scan)
        self.assertIn("家\n譜", scan.hannom_text)  # cache phẳng
        self.assertEqual(scan.ocr_vote_meta[0]["schema_version"], 2)  # danh sách vote trên UserScan
        self.assertEqual(self._run(scan, self._updated_record()), [])  # chạy lại: idempotent
        self.assertEqual(len(versions.list_by_scan(scan.id)), 2)

    def test_empty_corpus_value_never_erases(self) -> None:
        scan = self._imported_scan()
        self.assertEqual(self._run(scan, RECORD), [])  # record cũ (schema 1) → không làm gì


class PageVoteMetaTest(unittest.TestCase):
    def test_v1_keys_unchanged(self) -> None:
        l1 = {"voted_text": "家", "vote_method": "x", "engines": {}, "uncertain_rate": 0.5, "uncertain_spans": []}
        self.assertEqual(
            import_corpus._page_vote_meta(l1),
            {"vote_method": "x", "engines": {}, "uncertain_rate": 0.5, "uncertain_spans": [], "structural_diffs": None},
        )
        self.assertIsNone(import_corpus._page_vote_meta({"voted_text": "家"}))

    def test_v2_adds_lines_and_drops_voted_text(self) -> None:
        meta = import_corpus._page_vote_meta(_v2_l1("天地\n玄黃"))
        self.assertEqual((meta["lines"], "voted_text" in meta), (["天地", "玄黃"], False))

