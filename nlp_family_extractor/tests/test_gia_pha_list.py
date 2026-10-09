import unittest
from types import SimpleNamespace
from unittest import mock

from fastapi.testclient import TestClient

import api
from app.auth.dependencies import get_current_user, get_optional_current_user
from app.database import get_db
from app.workspace.gia_pha_list import GIA_PHA_CACHE, TtlCache, filter_items, normalize_for_search, paginate
from app.workspace.router import require_workspace_database
from tests.test_corpus_identifiers import _Db


def item(id_, title, *, ho=None, status="built", pending=False, source=None):
    return SimpleNamespace(id=id_, title=title, ho_toc=ho, status=status, ma_dinh_danh_pending=pending, ma_dinh_danh_nguon=source)


class PureLogicTest(unittest.TestCase):
    def test_normalize_matches_frontend_rules(self) -> None:
        self.assertEqual(normalize_for_search("  Phan Gia CÔNG Phả "), "phan gia cong pha")
        self.assertEqual(normalize_for_search("Đặng Đình"), "dang dinh")
        self.assertEqual(normalize_for_search("家譜 Nguyễn"), "家譜 nguyen")  # chữ Hán giữ nguyên

    def test_filter_by_terms_status_code_and_source(self) -> None:
        a = item("F-B-PN-1", "Phan gia công phả", ho="Phan", source="catalogue")
        b = item("nom-147", "Nguyễn tộc phả", ho="Nguyễn", status="pending", pending=True)
        c = item("F-A-NG-2", "Nguyễn đường", ho="Nguyễn", source="gemini")
        items = [a, b, c]
        self.assertEqual(filter_items(items, q="nguyen"), [b, c])
        self.assertEqual(filter_items(items, q="nguyen pha"), [b])  # mọi từ phải khớp
        self.assertEqual(filter_items(items, q="F-B"), [a])  # khớp cả mã
        self.assertEqual(filter_items(items, status="pending"), [b])
        self.assertEqual(filter_items(items, code="has"), [a, c])
        self.assertEqual(filter_items(items, code="none"), [b])
        self.assertEqual(filter_items(items, source="gemini"), [c])
        self.assertEqual(filter_items(items, q="  "), items)

    def test_paginate(self) -> None:
        data = list(range(1, 11))
        self.assertEqual(paginate(data, 1, 4), [1, 2, 3, 4])
        self.assertEqual(paginate(data, 3, 4), [9, 10])
        self.assertEqual(paginate(data, 4, 4), [])  # quá trang cuối: rỗng, không lỗi
        self.assertEqual(paginate(data, 1, 0), data)  # 0 = không phân trang
        self.assertEqual(paginate(data, 0, 3), [1, 2, 3])  # page<1 coi như 1

    def test_ttl_cache_expires_and_clears(self) -> None:
        now = [100.0]
        cache: TtlCache[str] = TtlCache(10, clock=lambda: now[0])
        cache.set("k", "v")
        self.assertEqual(cache.get("k"), "v")
        now[0] = 109.0
        self.assertEqual(cache.get("k"), "v")
        now[0] = 111.0
        self.assertIsNone(cache.get("k"))
        cache.set("k", "v2")
        cache.clear()
        self.assertIsNone(cache.get("k"))


class ListEndpointTest(_Db, unittest.TestCase):
    def setUp(self) -> None:
        super().setUp()
        GIA_PHA_CACHE.clear()
        for i in range(1, 26):  # 25 bộ chưa dựng cây
            scan = self.new_scan()
            self.scans.update(scan, title=f"Gia phả số {i:02d}" if i != 7 else "Nguyễn tộc phả")
        self.store = mock.Mock(list_trees=mock.Mock(return_value=[]), list_public_trees=mock.Mock(return_value=[]))
        self.patch = mock.patch.object(api, "_family_tree_store", self.store)
        self.patch.start()
        api.app.dependency_overrides[get_db] = lambda: self.db
        api.app.dependency_overrides[require_workspace_database] = lambda: None
        api.app.dependency_overrides[get_optional_current_user] = lambda: self.owner
        api.app.dependency_overrides[get_current_user] = lambda: self.owner
        self.client = TestClient(api.app)

    def tearDown(self) -> None:
        self.patch.stop()
        api.app.dependency_overrides.clear()
        GIA_PHA_CACHE.clear()
        super().tearDown()

    def get(self, **params):
        return self.client.get("/api/gia-pha", params=params).json()

    def test_backend_paginates_and_reports_totals(self) -> None:
        body = self.get(page=1, page_size=10)
        self.assertEqual((body["total"], body["total_all"], body["page"], body["page_size"], len(body["items"])), (25, 25, 1, 10, 10))
        last = self.get(page=3, page_size=10)
        self.assertEqual(len(last["items"]), 5)
        self.assertEqual(self.get(page=9, page_size=10)["items"], [])

    def test_default_returns_everything_for_old_callers(self) -> None:
        body = self.get()
        self.assertEqual((body["total"], len(body["items"]), body["page_size"]), (25, 25, 0))

    def test_search_runs_on_backend_and_total_is_filtered(self) -> None:
        body = self.get(q="nguyen", page=1, page_size=10)
        self.assertEqual((body["total"], body["total_all"]), (1, 25))
        self.assertEqual(body["items"][0]["title"], "Nguyễn tộc phả")
        self.assertEqual(self.get(q="zzz")["total"], 0)

    def test_filters_status_and_validation(self) -> None:
        self.assertEqual(self.get(status="built")["total"], 0)
        self.assertEqual(self.get(status="pending")["total"], 25)
        self.assertEqual(self.client.get("/api/gia-pha", params={"status": "bogus"}).status_code, 422)
        self.assertEqual(self.client.get("/api/gia-pha", params={"page_size": 1000}).status_code, 422)
        self.assertEqual(self.client.get("/api/gia-pha", params={"page": 0}).status_code, 422)

    def test_full_list_is_cached_across_filters_and_pages(self) -> None:
        self.get(page=1, page_size=10)
        self.get(page=2, page_size=10)
        self.get(q="nguyen")
        self.assertEqual(self.store.list_trees.call_count, 1)  # nguồn chỉ đọc 1 lần cho cả 3 request

    def test_write_request_clears_cache(self) -> None:
        self.get()
        self.assertEqual(self.store.list_trees.call_count, 1)
        self.client.post("/api/user/documents/999/restore")  # lỗi 4xx/403 → KHÔNG xoá cache
        self.get()
        self.assertEqual(self.store.list_trees.call_count, 1)
        scan_id = self.scans.list_all()[0].id
        ok = self.client.delete(f"/api/user/documents/{scan_id}")  # xoá mềm thành công → xoá cache
        self.assertEqual(ok.status_code, 200)
        body = self.get()
        self.assertEqual(body["total"], 24)  # bộ vừa xoá biến mất ngay, không phải chờ hết 20 giây
        self.assertEqual(self.store.list_trees.call_count, 2)


if __name__ == "__main__":
    unittest.main()
