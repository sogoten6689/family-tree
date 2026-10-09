import unittest
from unittest import mock

from app.auth.models import User, UserRole
from app.workspace.repository import GiaPhaPageRepository, GiaPhaVersionRepository, UserScanRepository
from tests.test_page_images import _PagesApi


class PageSoftDeleteTest(_PagesApi, unittest.TestCase):
    def url(self, tail: str = "") -> str:
        return f"/api/user/documents/{self.scan.id}/pages{tail}"

    def numbers(self) -> list[int]:
        return [p["page_number"] for p in self.client.get(self.url()).json()]

    def test_delete_hides_page_but_keeps_content_and_recounts(self) -> None:
        res = self.client.delete(self.url("/2"))
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.json(), {"page_number": 2, "deleted": True, "active_pages": 3})
        self.assertEqual(self.numbers(), [1, 3, 4])
        self.assertEqual(self.client.get(self.url("/2")).status_code, 404)
        self.assertEqual(self.client.patch(self.url("/2"), json={"hannom_text": "x"}).status_code, 404)
        self.db.refresh(self.scan)
        self.assertEqual(self.scan.page_count, 3)
        self.assertNotIn("漢2", self.scan.hannom_text)  # văn bản gộp không còn trang đã xoá
        pages = GiaPhaPageRepository(self.db)
        deleted = pages.list_deleted_by_scan(self.scan.id)[0]  # hàng và nội dung vẫn còn trong DB
        self.assertEqual(
            [c.hannom_text for c in pages.list_content_for_version(self.version.id) if c.page_id == deleted.id], ["漢2"]
        )

    def test_delete_twice_is_404_and_listing_shows_deleted(self) -> None:
        self.assertEqual(self.client.delete(self.url("/3")).status_code, 200)
        self.assertEqual(self.client.delete(self.url("/3")).status_code, 404)
        items = self.client.get(self.url("/deleted")).json()  # không bị nuốt bởi /pages/{n}
        self.assertEqual([(i["page_number"], i["hannom_text"]) for i in items], [(3, "漢3")])
        self.assertIsNotNone(items[0]["deleted_at"])

    def test_restore_brings_back_same_page_and_text(self) -> None:
        self.client.delete(self.url("/2"))
        res = self.client.post(self.url("/2/restore"))
        self.assertEqual(res.json(), {"page_number": 2, "deleted": False, "active_pages": 4})
        self.assertEqual(self.numbers(), [1, 2, 3, 4])
        self.assertEqual(self.client.get(self.url("/2")).json()["hannom_text"], "漢2")
        self.db.refresh(self.scan)
        self.assertEqual(self.scan.page_count, 4)
        self.assertIn("漢2", self.scan.hannom_text)
        self.assertEqual(self.client.post(self.url("/2/restore")).status_code, 404)  # đang không xoá
        self.assertEqual(self.client.post(self.url("/99/restore")).status_code, 404)

    def test_other_user_cannot_delete_or_restore(self) -> None:
        self.client.delete(self.url("/1"))
        self.user = self.db.query(User).filter_by(email="o@x.l").one()
        self.assertEqual(self.client.delete(self.url("/2")).status_code, 404)
        self.assertEqual(self.client.post(self.url("/1/restore")).status_code, 404)
        self.assertEqual(self.client.get(self.url("/deleted")).status_code, 404)
        self.assertEqual(len(GiaPhaPageRepository(self.db).list_by_scan(self.scan.id)), 3)

    def test_import_tools_still_see_deleted_pages(self) -> None:
        self.client.delete(self.url("/2"))
        pages = GiaPhaPageRepository(self.db)
        self.assertEqual([p.page_number for p in pages.list_by_scan(self.scan.id)], [1, 3, 4])
        self.assertEqual([p.page_number for p in pages.list_by_scan(self.scan.id, include_deleted=True)], [1, 2, 3, 4])


class ScanSoftDeleteTest(_PagesApi, unittest.TestCase):
    def setUp(self) -> None:
        super().setUp()
        self.admin = self.owner  # _Db tạo owner là ADMIN
        self.plain = self.db.query(User).filter_by(email="o@x.l").one()
        self.user = self.admin

    def test_only_admin_can_delete_and_scan_disappears_everywhere(self) -> None:
        self.user = self.plain
        self.assertEqual(self.client.delete(f"/api/user/documents/{self.scan.id}").status_code, 403)
        self.user = self.admin
        res = self.client.delete(f"/api/user/documents/{self.scan.id}")
        self.assertEqual(res.status_code, 200)
        self.assertIsNotNone(res.json()["deleted_at"])
        self.assertEqual(self.client.get(f"/api/user/documents/{self.scan.id}").status_code, 404)
        self.assertEqual(self.client.get(f"/api/user/documents/{self.scan.id}/pages").status_code, 404)
        scans = UserScanRepository(self.db)
        self.assertEqual(scans.list_all(), [])
        self.assertEqual(scans.list_by_user(self.admin.id), [])
        self.assertEqual(scans.count_by_user(self.admin.id), 0)
        self.assertEqual(len(scans.list_by_user(self.admin.id, include_deleted=True)), 1)  # import tool vẫn thấy
        self.assertEqual(self.client.delete(f"/api/user/documents/{self.scan.id}").status_code, 404)

    def test_admin_lists_and_restores_deleted_scan_with_data_intact(self) -> None:
        self.client.delete(f"/api/user/documents/{self.scan.id}")
        listing = self.client.get("/api/admin/documents/deleted").json()
        self.assertEqual((listing["total"], listing["items"][0]["id"]), (1, self.scan.id))
        self.user = self.plain
        self.assertEqual(self.client.get("/api/admin/documents/deleted").status_code, 403)
        self.assertEqual(self.client.post(f"/api/user/documents/{self.scan.id}/restore").status_code, 403)
        self.user = self.admin
        self.assertEqual(self.client.post(f"/api/user/documents/{self.scan.id}/restore").status_code, 200)
        self.assertEqual(self.client.get("/api/admin/documents/deleted").json()["total"], 0)
        pages = self.client.get(f"/api/user/documents/{self.scan.id}/pages").json()
        self.assertEqual([(p["page_number"], p["hannom_text"]) for p in pages][:2], [(1, "漢1"), (2, "漢2")])
        self.assertEqual(self.client.post(f"/api/user/documents/{self.scan.id}/restore").status_code, 404)

    @mock.patch("app.workspace.router.database_enabled", return_value=True)  # endpoint gọi thẳng, không qua Depends
    def test_public_hannom_progress_excludes_deleted_scan(self, _db_enabled) -> None:
        self.scan.request_id = "hannom-corpus:demo-1"
        self.scan.hannom_text = "漢"
        self.scan.page_count = 4
        self.db.commit()
        before = self.client.get("/api/public/hannom-progress").json()
        self.assertEqual((before["total_books"], before["total_pages"]), (1, 4))
        self.client.delete(f"/api/user/documents/{self.scan.id}")
        after = self.client.get("/api/public/hannom-progress").json()
        self.assertEqual((after["total_books"], after["total_pages"], after["books"]), (0, 0, []))
        self.client.post(f"/api/user/documents/{self.scan.id}/restore")
        self.assertEqual(self.client.get("/api/public/hannom-progress").json()["total_books"], 1)

    def test_ma_dinh_danh_stays_reserved_after_delete(self) -> None:
        scans = UserScanRepository(self.db)
        self.scan.ma_dinh_danh = "F-A-NG-X-001-1900"
        self.db.commit()
        self.client.delete(f"/api/user/documents/{self.scan.id}")
        taken = self.db.query(type(self.scan)).filter_by(ma_dinh_danh="F-A-NG-X-001-1900").count()
        self.assertEqual(taken, 1)  # hàng còn đó → logic tránh trùng mã vẫn thấy mã này


if __name__ == "__main__":
    unittest.main()
