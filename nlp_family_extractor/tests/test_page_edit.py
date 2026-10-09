import unittest

from fastapi.testclient import TestClient

import api
from app.auth.models import User, UserRole
from app.workspace.repository import GiaPhaPageRepository, GiaPhaVersionRepository
from tests.test_page_images import _PagesApi


class PageEditTest(_PagesApi, unittest.TestCase):
    def url(self, n: int = 1) -> str:
        return f"/api/user/documents/{self.scan.id}/pages/{n}"

    def texts(self, version_id: int) -> dict[int, str]:
        pages = GiaPhaPageRepository(self.db)
        by_id = {p.id: p.page_number for p in pages.list_by_scan(self.scan.id)}
        return {by_id[c.page_id]: c.hannom_text for c in pages.list_content_for_version(version_id)}

    def test_first_edit_forks_and_keeps_original(self) -> None:
        res = self.client.patch(self.url(2), json={"hannom_text": "新字"})
        self.assertEqual(res.status_code, 200)
        body = res.json()
        self.assertTrue(body["forked"])
        self.assertEqual(body["version"]["source"], "manual-edit")
        self.assertFalse(body["version"]["is_current"])
        self.assertEqual(body["version"]["parent_version_id"], self.version.id)
        self.assertEqual(body["page"]["hannom_text"], "新字")
        self.assertEqual(body["page"]["translation_text"], "dịch 2")  # trường không gửi giữ nguyên
        self.assertEqual(self.texts(self.version.id)[2], "漢2")  # bản gốc không đổi
        self.assertEqual(self.texts(body["version"]["version_id"]), {1: "漢1", 2: "新字", 3: "漢3", 4: "漢4"})

    def test_second_edit_with_version_id_edits_in_place(self) -> None:
        first = self.client.patch(self.url(1), json={"hannom_text": "A"}).json()
        vid = first["version"]["version_id"]
        second = self.client.patch(self.url(3), json={"hannom_text": "B", "version_id": vid}).json()
        self.assertFalse(second["forked"])
        self.assertEqual(second["version"]["version_id"], vid)
        self.assertEqual(len(GiaPhaVersionRepository(self.db).list_by_scan(self.scan.id)), 2)
        self.assertEqual((self.texts(vid)[1], self.texts(vid)[3]), ("A", "B"))

    def test_empty_string_clears_but_none_keeps(self) -> None:
        body = self.client.patch(self.url(1), json={"translation_text": ""}).json()
        self.assertEqual((body["page"]["hannom_text"], body["page"]["translation_text"]), ("漢1", ""))

    def test_current_version_edit_syncs_flat_cache(self) -> None:
        first = self.client.patch(self.url(1), json={"hannom_text": "NEW"}).json()
        vid = first["version"]["version_id"]
        GiaPhaVersionRepository(self.db).set_current(self.scan.id, vid)
        self.client.patch(self.url(2), json={"hannom_text": "NEW2", "version_id": vid})
        self.db.refresh(self.scan)
        self.assertIn("NEW2", self.scan.hannom_text)

    def test_validation_and_access(self) -> None:
        self.assertEqual(self.client.patch(self.url(1), json={}).status_code, 400)
        self.assertEqual(self.client.patch(self.url(99), json={"hannom_text": "x"}).status_code, 404)
        self.assertEqual(self.client.patch(self.url(1), json={"hannom_text": "x", "version_id": 999}).status_code, 404)
        self.user = self.db.query(User).filter_by(email="o@x.l").one()  # người lạ, không phải chủ bộ
        self.assertEqual(self.client.patch(self.url(1), json={"hannom_text": "x"}).status_code, 404)
        self.assertEqual(len(GiaPhaVersionRepository(self.db).list_by_scan(self.scan.id)), 1)


if __name__ == "__main__":
    unittest.main()
