import unittest
from unittest import mock

from app.auth.models import User
from app.workspace.page_images import replacement_image_key, sniff_image
from app.workspace.repository import GiaPhaPageRepository
from tests.test_page_images import _PagesApi

JPG = b"\xff\xd8\xff\xe0" + b"0" * 32
PNG = b"\x89PNG\r\n\x1a\n" + b"0" * 32
WEBP = b"RIFF\x10\x00\x00\x00WEBPVP8 " + b"0" * 16


class SniffTest(unittest.TestCase):
    def test_detects_by_signature_not_name(self) -> None:
        self.assertEqual(sniff_image(JPG), (".jpg", "image/jpeg"))
        self.assertEqual(sniff_image(PNG), (".png", "image/png"))
        self.assertEqual(sniff_image(WEBP), (".webp", "image/webp"))
        self.assertEqual(sniff_image(b"II*\x00rest")[1], "image/tiff")
        self.assertIsNone(sniff_image(b"<html>not an image</html>"))
        self.assertIsNone(sniff_image(b"%PDF-1.7"))

    def test_replacement_key_is_new_each_time(self) -> None:
        a, b = replacement_image_key(7, 3, ".png"), replacement_image_key(7, 3, ".png")
        self.assertNotEqual(a, b)
        self.assertTrue(a.startswith("gia-pha/7/pages/003-") and a.endswith(".png"))


class ReplaceImageTest(_PagesApi, unittest.TestCase):
    def setUp(self) -> None:
        super().setUp()
        self.patch.stop()  # _PagesApi giấu mock storage trong biến cục bộ → dựng lại để kiểm tra lời gọi
        self.storage = mock.Mock()
        self.storage.config.enabled = True
        self.storage.get_presigned_url.side_effect = lambda key: f"https://minio/{key}?sig"
        self.patch = mock.patch("app.documents.storage.ObjectStorage.from_env", return_value=self.storage)
        self.patch.start()

    def url(self, n: int = 1) -> str:
        return f"/api/user/documents/{self.scan.id}/pages/{n}/image"

    def put(self, data: bytes, n: int = 1, name: str = "x.jpg"):
        return self.client.put(self.url(n), files={"file": (name, data, "application/octet-stream")})

    def page_key(self, n: int = 1) -> str:
        return GiaPhaPageRepository(self.db).list_by_scan(self.scan.id)[n - 1].image_file_key

    def test_replaces_with_new_key_and_keeps_old_object(self) -> None:
        old = self.page_key(2)
        res = self.put(PNG, n=2, name="trang.jpg")  # tên .jpg nhưng nội dung PNG → theo chữ ký
        self.assertEqual(res.status_code, 200)
        body = res.json()
        new = self.page_key(2)
        self.assertNotEqual(new, old)
        self.assertTrue(new.startswith(f"gia-pha/{self.scan.id}/pages/002-") and new.endswith(".png"))
        self.assertEqual(body["previous_image_key"], old)
        self.assertEqual(body["page"]["image_url"], f"https://minio/{new}?sig")
        self.assertEqual((body["page"]["hannom_text"], body["page"]["translation_text"]), ("漢2", "dịch 2"))
        key, _file = self.storage.upload_file.call_args.args
        self.assertEqual(key, new)
        self.assertEqual(self.storage.upload_file.call_args.kwargs["content_type"], "image/png")
        self.storage.delete_file.assert_not_called()  # object cũ giữ nguyên để hoàn tác

    def test_rejects_non_image_empty_and_oversize_without_touching_db(self) -> None:
        before = self.page_key(1)
        self.assertEqual(self.put(b"%PDF-1.7 not image").status_code, 400)
        self.assertEqual(self.put(b"").status_code, 400)
        with mock.patch.dict("os.environ", {"MINIO_MAX_UPLOAD_BYTES": "16"}):
            self.assertEqual(self.put(JPG).status_code, 400)
        self.storage.upload_file.assert_not_called()
        self.assertEqual(self.page_key(1), before)

    def test_upload_failure_keeps_old_key(self) -> None:
        from app.documents.storage import ObjectStorageError

        before = self.page_key(1)
        self.storage.upload_file.side_effect = ObjectStorageError("down")
        self.assertEqual(self.put(JPG).status_code, 502)
        self.assertEqual(self.page_key(1), before)

    def test_storage_disabled_and_missing_page_and_other_user(self) -> None:
        self.assertEqual(self.put(JPG, n=99).status_code, 404)
        self.storage.config.enabled = False
        self.assertEqual(self.put(JPG).status_code, 503)
        self.storage.config.enabled = True
        self.user = self.db.query(User).filter_by(email="o@x.l").one()
        before = self.page_key(1)
        self.assertEqual(self.put(JPG).status_code, 404)
        self.assertEqual(self.page_key(1), before)


if __name__ == "__main__":
    unittest.main()
