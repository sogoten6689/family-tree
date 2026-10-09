import unittest
from unittest import mock

from app.auth.models import User
from app.hannom.engines import EngineResult
from app.workspace.repository import GiaPhaPageRepository, GiaPhaVersionRepository
from tests.test_page_images import _PagesApi

BOX = {"bbox_xyxy": [1, 2, 3, 4], "han": "新", "confidence": 0.9, "order": 1}


class PageOcrTest(_PagesApi, unittest.TestCase):
    def setUp(self) -> None:
        super().setUp()
        self.patch.stop()
        self.storage = mock.Mock()
        self.storage.config.enabled = True
        self.storage.read_file_bytes.return_value = b"\xff\xd8\xffIMG"
        self.patch = mock.patch("app.documents.storage.ObjectStorage.from_env", return_value=self.storage)
        self.patch.start()
        pages = GiaPhaPageRepository(self.db)
        for p in pages.list_by_scan(self.scan.id):  # ảnh đã lên MinIO (fixture mặc định chỉ là đường dẫn repo)
            pages.set_image_key(p, f"gia-pha/{self.scan.id}/pages/{p.page_number:03d}.jpg")
        self.ocr = mock.patch(
            "app.hannom.engines.run_kimhannom",
            return_value=EngineResult(engine="kimhannom", lines=["新字一", "新字二"], bbox=[BOX]),
        )
        self.run = self.ocr.start()

    def tearDown(self) -> None:
        self.ocr.stop()
        super().tearDown()

    def url(self, n: int = 1) -> str:
        return f"/api/user/documents/{self.scan.id}/pages/{n}/ocr"

    def post(self, n: int = 1, **body):
        return self.client.post(self.url(n), json={"confirm_paid": True, **body})

    def content(self, version_id: int, page_number: int):
        pages = GiaPhaPageRepository(self.db)
        pid = pages.list_by_scan(self.scan.id)[page_number - 1].id
        return next(c for c in pages.list_content_for_version(version_id) if c.page_id == pid)

    def test_requires_explicit_paid_confirmation(self) -> None:
        self.assertEqual(self.client.post(self.url(), json={}).status_code, 400)
        self.assertEqual(self.client.post(self.url(), json={"confirm_paid": False}).status_code, 400)
        self.run.assert_not_called()
        self.storage.read_file_bytes.assert_not_called()

    def test_ocr_forks_version_writes_text_and_boxes_keeps_original(self) -> None:
        res = self.post(n=2)
        self.assertEqual(res.status_code, 200)
        body = res.json()
        self.assertTrue(body["forked"])
        self.assertEqual((body["engine"], body["box_count"]), ("kimhannom", 1))
        self.assertFalse(body["version"]["is_current"])
        self.assertEqual(body["version"]["source"], "manual-edit")
        self.assertEqual(body["page"]["hannom_text"], "新字一\n新字二")
        self.assertEqual(body["page"]["translation_text"], "dịch 2")  # giữ theo chữ cũ
        self.assertTrue(body["downstream_stale"])
        new = self.content(body["version"]["version_id"], 2)
        self.assertEqual(new.ocr_bbox, [BOX])
        self.assertIsNone(new.ocr_vote_meta)
        old = self.content(self.version.id, 2)
        self.assertEqual(old.hannom_text, "漢2")  # bản gốc không đổi
        self.run.assert_called_once()

    def test_second_ocr_with_version_id_reuses_working_version(self) -> None:
        first = self.post(n=1).json()
        vid = first["version"]["version_id"]
        second = self.post(n=3, version_id=vid).json()
        self.assertFalse(second["forked"])
        self.assertEqual(second["version"]["version_id"], vid)
        self.assertEqual(len(GiaPhaVersionRepository(self.db).list_by_scan(self.scan.id)), 2)

    def test_engine_failure_creates_no_version(self) -> None:
        self.run.return_value = None
        self.assertEqual(self.post().status_code, 502)
        self.run.return_value = EngineResult(engine="kimhannom", lines=["  "], bbox=None)
        self.assertEqual(self.post().status_code, 502)
        self.assertEqual(len(GiaPhaVersionRepository(self.db).list_by_scan(self.scan.id)), 1)

    def test_image_not_on_minio_or_storage_down(self) -> None:
        pages = GiaPhaPageRepository(self.db)
        pages.set_image_key(pages.list_by_scan(self.scan.id)[3], "data/00_raw/a/004.pdf")
        self.assertEqual(self.post(n=4).status_code, 409)
        self.storage.config.enabled = False
        self.assertEqual(self.post().status_code, 503)
        self.run.assert_not_called()

    def test_unknown_engine_missing_page_and_other_user(self) -> None:
        self.assertEqual(self.post(engine="gemini_vision").status_code, 400)
        self.assertEqual(self.post(n=99).status_code, 404)
        self.user = self.db.query(User).filter_by(email="o@x.l").one()
        self.assertEqual(self.post().status_code, 404)
        self.run.assert_not_called()
        self.assertEqual(len(GiaPhaVersionRepository(self.db).list_by_scan(self.scan.id)), 1)


if __name__ == "__main__":
    unittest.main()
