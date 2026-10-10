import unittest
from unittest import mock

from fastapi.testclient import TestClient
from sqlalchemy import event

import api
from app.auth.dependencies import get_current_user, get_optional_current_user
from app.database import get_db
from app.workspace.gia_pha_list import GIA_PHA_CACHE
from app.workspace.router import require_workspace_database
from app.workspace.stats import STATS_CACHE
from tests.test_corpus_identifiers import _Db


class HannomProgressTest(_Db, unittest.TestCase):
    def setUp(self) -> None:
        super().setUp()
        GIA_PHA_CACHE.clear()
        STATS_CACHE.clear()
        rows = [  # (doc_id, trang, hán, phiên âm, dịch)
            ("b-sach", 10, "漢", "Hán", "dịch"),
            ("a-sach", 4, "漢", "", None),  # chuỗi rỗng và NULL đều là "chưa có"
            ("c-sach", 6, None, None, None),
        ]
        for doc_id, pages, han, translit, dich in rows:
            scan = self.new_scan()
            scan.file_name = doc_id
            scan.title = f"Sách {doc_id}"
            scan.request_id = f"hannom-corpus:{doc_id}"
            scan.page_count = pages
            scan.hannom_text, scan.transliteration_text, scan.source_text = han, translit, dich
        other = self.new_scan()  # không thuộc corpus Hán Nôm → không tính
        other.request_id = "khac:1"
        other.page_count = 99
        self.db.commit()
        api.app.dependency_overrides[get_db] = lambda: self.db
        api.app.dependency_overrides[require_workspace_database] = lambda: None
        api.app.dependency_overrides[get_optional_current_user] = lambda: None
        api.app.dependency_overrides[get_current_user] = lambda: self.owner
        self.patch_db = mock.patch("app.workspace.router.database_enabled", return_value=True)  # endpoint gọi thẳng
        self.patch_db.start()
        self.client = TestClient(api.app)

    def tearDown(self) -> None:
        self.patch_db.stop()
        api.app.dependency_overrides.clear()
        STATS_CACHE.clear()
        super().tearDown()

    def test_counts_flags_and_sort_order(self) -> None:
        body = self.client.get("/api/public/hannom-progress").json()
        self.assertEqual((body["total_books"], body["total_pages"]), (3, 20))
        self.assertEqual(body["pages_with_ocr"], 14)  # 10 + 4
        self.assertEqual(body["pages_with_transliteration"], 10)  # chuỗi rỗng không tính
        self.assertEqual(body["pages_with_translation"], 10)
        self.assertEqual((body["ocr_percent"], body["transliteration_percent"]), (70.0, 50.0))
        self.assertEqual([b["doc_id"] for b in body["books"]], ["a-sach", "b-sach", "c-sach"])
        a = body["books"][0]
        self.assertEqual((a["has_ocr"], a["has_transliteration"], a["has_translation"]), (True, False, False))

    def test_second_call_is_served_from_cache_without_sql(self) -> None:
        self.client.get("/api/public/hannom-progress")
        statements: list[str] = []
        event.listen(self.db.get_bind(), "before_cursor_execute", lambda *a: statements.append(a[2]))
        self.client.get("/api/public/hannom-progress")
        self.assertEqual(statements, [])

    def test_does_not_load_text_columns_into_python(self) -> None:
        statements: list[str] = []
        event.listen(self.db.get_bind(), "before_cursor_execute", lambda *a: statements.append(a[2]))
        self.client.get("/api/public/hannom-progress")
        select_list = statements[-1].split(" FROM ")[0]
        # Chỉ được dùng cột văn bản trong biểu thức CASE (để hỏi có/không), không SELECT thẳng cột.
        for column in ("hannom_text", "transliteration_text", "source_text"):
            self.assertNotIn(f"user_scans.{column},", select_list.replace("CASE", "\nCASE"))
            self.assertNotIn(f"user_scans.{column} AS", select_list)

    def test_write_request_clears_cache(self) -> None:
        self.assertEqual(self.client.get("/api/public/hannom-progress").json()["total_books"], 3)
        target = next(sc for sc in self.scans.list_all() if sc.file_name == "b-sach")
        self.assertEqual(self.client.delete(f"/api/user/documents/{target.id}").status_code, 200)  # xoá mềm (admin)
        body = self.client.get("/api/public/hannom-progress").json()  # không phải chờ hết hạn cache
        self.assertEqual(body["total_books"], 2)
        self.assertEqual([b["doc_id"] for b in body["books"]], ["a-sach", "c-sach"])
        self.assertEqual(body["total_pages"], 10)

if __name__ == "__main__":
    unittest.main()
