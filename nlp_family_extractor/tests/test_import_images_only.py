import tempfile
import unittest
from pathlib import Path

from sqlalchemy import select

from app.workspace.models import GiaPhaPage, OcrStatus, UserScan
from tests.test_corpus_identifiers import _Db
from tools import import_hannom_images_only as imp


class ImportImagesOnlyTest(_Db, unittest.TestCase):
    def setUp(self) -> None:
        super().setUp()
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.hannom = self.root / "hannom"
        pages = self.hannom / "nomfoundation/volumes/595/pages"
        pages.mkdir(parents=True)
        for name in ("002.jpg", "001.jpg", "003.jpg", "001-boundingbox-preview.jpg", ".DS_Store", "note.txt"):
            (pages / name).write_bytes(b"x")
        self.books = [
            {"doc_id": "nom-595", "folder": "nomfoundation/volumes/595/pages", "title": "Tả Thanh Oai"},
            {"doc_id": "nom-000", "folder": "nomfoundation/volumes/000/pages", "title": "Không có ảnh"},
        ]

    def tearDown(self) -> None:
        self.tmp.cleanup()
        super().tearDown()

    def run_import(self, **kw):
        return imp.import_books(self.db, owner_id=self.owner.id, hannom_root=self.hannom, relative_to=self.root, books=self.books, log=lambda *_: None, **kw)

    def test_list_images_skips_previews_hidden_and_non_images_in_name_order(self) -> None:
        names = [p.name for p in imp.list_images(self.hannom / "nomfoundation/volumes/595/pages")]
        self.assertEqual(names, ["001.jpg", "002.jpg", "003.jpg"])

    def test_creates_scan_version_and_pages_without_ocr(self) -> None:
        stats = self.run_import()
        self.assertEqual((stats["created"], stats["empty"], stats["pages"]), (1, 1, 3))
        scan = self.db.scalar(select(UserScan).where(UserScan.request_id == "hannom-corpus:img-nom-595"))
        self.assertEqual((scan.page_count, scan.ocr_status, scan.file_type), (3, OcrStatus.PENDING, "hannom-corpus"))
        self.assertIsNone(scan.hannom_text)
        keys = [p.image_file_key for p in self.db.scalars(select(GiaPhaPage).where(GiaPhaPage.user_scan_id == scan.id).order_by(GiaPhaPage.page_number))]
        self.assertEqual(keys, [f"hannom/nomfoundation/volumes/595/pages/00{i}.jpg" for i in (1, 2, 3)])
        self.assertTrue((self.root / keys[0]).is_file())  # đường dẫn tương đối khớp tệp thật

    def test_rerun_is_idempotent(self) -> None:
        self.run_import()
        stats = self.run_import()
        self.assertEqual((stats["created"], stats["existing"]), (0, 1))
        self.assertEqual(len(self.db.scalars(select(UserScan).where(UserScan.request_id == "hannom-corpus:img-nom-595")).all()), 1)

    def test_dry_run_writes_nothing(self) -> None:
        stats = self.run_import(dry_run=True)
        self.assertEqual((stats["created"], stats["pages"]), (0, 3))
        self.assertIsNone(self.db.scalar(select(UserScan).where(UserScan.request_id == "hannom-corpus:img-nom-595")))


if __name__ == "__main__":
    unittest.main()
