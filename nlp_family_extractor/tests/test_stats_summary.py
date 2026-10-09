import unittest
from types import SimpleNamespace
from unittest import mock

from fastapi.testclient import TestClient

import api
from app.auth.dependencies import get_current_user, get_optional_current_user
from app.auth.models import User, UserRole
from app.database import get_db
from app.workspace.gia_pha_list import GIA_PHA_CACHE
from app.workspace.router import require_workspace_database
from app.workspace.stats import STATS_CACHE, page_progress, percent, summarize_items
from tests.test_corpus_identifiers import _Db


def it(id_, *, status="built", pending=False, src=None, ho=None, nodes=None, public=None):
    return SimpleNamespace(id=id_, status=status, ma_dinh_danh_pending=pending, ma_dinh_danh_nguon=src,
                           ho_toc=ho, node_count=nodes, is_public=public)


class PureTest(unittest.TestCase):
    def test_percent_handles_zero_total(self) -> None:
        self.assertEqual(percent(1, 3), 33.3)
        self.assertEqual(percent(5, 0), 0.0)

    def test_summarize_items(self) -> None:
        items = [
            it("a", src="catalogue", ho="Phan", nodes=10, public=True),
            it("b", src="gemini", ho="Nguyễn", nodes=4),
            it("c", status="pending", pending=True, ho="Nguyễn"),
            it("d", src="other-src", ho=" Nguyễn "),
            it("e", status="pending", pending=True),
        ]
        s = summarize_items(items)
        self.assertEqual((s["total"], s["built"], s["pending"]), (5, 3, 2))
        self.assertEqual((s["with_code"], s["without_code"]), (3, 2))
        self.assertEqual(s["code_source"], {"catalogue": 1, "gemini": 1, "other": 1})
        self.assertEqual((s["public_trees"], s["nodes"]), (1, 14))
        self.assertEqual(s["top_ho_toc"], [{"ho_toc": "Nguyễn", "count": 3}, {"ho_toc": "Phan", "count": 1}])

    def test_page_progress(self) -> None:
        p = page_progress({"scans": 2, "pages": 200, "ocr_pages": 150, "transliteration_pages": 100, "translation_pages": 200})
        self.assertEqual((p["ocr_percent"], p["transliteration_percent"], p["translation_percent"]), (75.0, 50.0, 100.0))
        self.assertEqual(page_progress({})["ocr_percent"], 0.0)


class SummaryEndpointTest(_Db, unittest.TestCase):
    def setUp(self) -> None:
        super().setUp()
        GIA_PHA_CACHE.clear()
        STATS_CACHE.clear()
        # 3 bộ (admin sở hữu): bộ 1 có chữ Hán+phiên âm+dịch (10 trang), bộ 2 chỉ chữ Hán (4 trang), bộ 3 trống (6 trang)
        a = self.new_scan(); b = self.new_scan(); c = self.new_scan()
        self.scans.update(a, title="Có đủ", hannom_text="漢", transliteration_text="Hán", source_text="dịch")
        self.scans.update(b, title="Chỉ Hán", hannom_text="漢")
        self.scans.update(c, title="Trống")
        for scan, pages in ((a, 10), (b, 4), (c, 6)):
            scan.page_count = pages
        self.db.commit()
        self.scans.set_corpus_identifiers(a, {"ma_dinh_danh": "F-B-PN-X-001-1930"})
        self.store = mock.Mock(list_trees=mock.Mock(return_value=[]), list_public_trees=mock.Mock(return_value=[]), list_trees_by_user=mock.Mock(return_value=[]))
        self.patch = mock.patch.object(api, "_family_tree_store", self.store)
        self.patch.start()
        api.app.dependency_overrides[get_db] = lambda: self.db
        api.app.dependency_overrides[require_workspace_database] = lambda: None
        self.user = self.owner
        api.app.dependency_overrides[get_optional_current_user] = lambda: self.user
        api.app.dependency_overrides[get_current_user] = lambda: self.user
        self.client = TestClient(api.app)

    def tearDown(self) -> None:
        self.patch.stop()
        api.app.dependency_overrides.clear()
        GIA_PHA_CACHE.clear()
        STATS_CACHE.clear()
        super().tearDown()

    def summary(self, **params):
        return self.client.get("/api/gia-pha/summary", params=params).json()

    def test_admin_summary_counts_and_page_progress(self) -> None:
        s = self.summary()
        self.assertEqual(s["scope"], "admin")
        self.assertEqual((s["total"], s["built"], s["pending"]), (3, 0, 3))
        self.assertEqual(s["pages"]["pages"], 20)
        self.assertEqual((s["pages"]["ocr_pages"], s["pages"]["transliteration_pages"], s["pages"]["translation_pages"]), (14, 10, 10))
        self.assertEqual((s["pages"]["ocr_percent"], s["pages"]["transliteration_percent"]), (70.0, 50.0))
        self.assertIn("generated_at", s)

    def test_guest_gets_no_private_page_stats(self) -> None:
        self.user = None
        s = self.summary()
        self.assertEqual(s["scope"], "public")
        self.assertIsNone(s["pages"])
        self.assertEqual(s["total"], 0)

    def test_regular_user_only_sees_own_scans(self) -> None:
        other = User(email="u@x.l", full_name="U", password_hash="x", role=UserRole.USER)
        self.db.add(other); self.db.commit()
        self.user = other
        s = self.summary()
        self.assertEqual((s["scope"], s["total"], s["pages"]["pages"]), ("user", 0, 0))

    def test_summary_is_cached_and_cleared_by_writes(self) -> None:
        self.summary()
        self.summary()
        self.assertEqual(self.store.list_trees.call_count, 1)  # lần 2 từ cache
        self.summary(refresh="true")
        self.assertEqual(self.store.list_trees.call_count, 2)  # refresh bỏ qua cache
        scan_id = self.scans.list_all()[0].id
        self.assertEqual(self.client.delete(f"/api/user/documents/{scan_id}").status_code, 200)
        s = self.summary()
        self.assertEqual((s["total"], s["pages"]["scans"]), (2, 2))  # bộ vừa xoá mềm biến mất khỏi thống kê ngay

    def test_admin_stats_cached_and_excludes_soft_deleted(self) -> None:
        stats = self.client.get("/api/admin/stats").json()
        self.assertEqual(stats["total_scans"], 3)
        self.client.get("/api/admin/stats")
        self.assertEqual(self.store.list_trees.call_count, 1)  # lần 2 từ cache
        scan_id = self.scans.list_all()[0].id
        self.client.delete(f"/api/user/documents/{scan_id}")
        self.assertEqual(self.client.get("/api/admin/stats").json()["total_scans"], 2)  # không đếm bộ đã xoá mềm


if __name__ == "__main__":
    unittest.main()
