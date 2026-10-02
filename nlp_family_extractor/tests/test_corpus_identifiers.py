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
