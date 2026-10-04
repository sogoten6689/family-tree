import importlib.util
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from fastapi.testclient import TestClient

import api
from app.auth.dependencies import get_current_user
from app.auth.models import User, UserRole
from app.database import get_db
from app.workspace.page_images import is_storage_key, page_image_key
from app.workspace.repository import GiaPhaPageRepository, GiaPhaVersionRepository
from app.workspace.router import require_workspace_database
from tests.test_corpus_identifiers import _Db

_spec = importlib.util.spec_from_file_location(
    "upload_images", Path(__file__).resolve().parents[1] / "tools" / "upload_gia_pha_page_images.py"
)
upload_images = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(upload_images)


class KeyTest(unittest.TestCase):
    def test_key_is_stable_and_keeps_extension(self) -> None:
        self.assertEqual(page_image_key(20, 7, "data/00_raw/x/pages/007.JPG"), "gia-pha/20/pages/007.jpg")
        self.assertTrue(is_storage_key("gia-pha/20/pages/007.jpg"))
        self.assertFalse(is_storage_key("data/00_raw/x.jpg"))
        self.assertFalse(is_storage_key(None))


class _Pages(_Db):
    def setUp(self) -> None:
        super().setUp()
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        scan = self.new_scan()
        self.scan = scan
        pages = GiaPhaPageRepository(self.db)
        self.version = GiaPhaVersionRepository(self.db).create_version(user_scan_id=scan.id, make_current=True)
        self.db.commit()
        for n, img in ((1, "data/00_raw/a/001.jpg"), (2, "data/00_raw/a/002.png"), (3, "data/00_raw/a/003.jpg"), (4, "data/00_raw/a/004.pdf")):
            page = pages.create_page(user_scan_id=scan.id, page_number=n, image_file_key=img)
            pages.upsert_content(version_id=self.version.id, page_id=page.id, hannom_text=f"漢{n}", translation_text=f"dịch {n}")
        for img in ("001.jpg", "002.png", "004.pdf"):  # 003.jpg thiếu
            (self.root / "data/00_raw/a").mkdir(parents=True, exist_ok=True)
            (self.root / "data/00_raw/a" / img).write_bytes(b"img")

    def tearDown(self) -> None:
        self.tmp.cleanup()
        super().tearDown()


class UploadScriptTest(_Pages, unittest.TestCase):
    def _run(self, dry_run, existing=()):
        uploaded = []
        stats = upload_images.upload_page_images(
            self.db,
            image_root=self.root,
            object_exists=lambda key: key in existing,
            upload=lambda key, path, ctype: uploaded.append((key, path.name, ctype)),
            dry_run=dry_run,
            log=lambda msg: None,
        )
        return stats, uploaded

    def keys(self):
        return [p.image_file_key for p in GiaPhaPageRepository(self.db).list_by_scan(self.scan.id)]

    def test_dry_run_counts_without_writing(self) -> None:
        stats, uploaded = self._run(dry_run=True)
        self.assertEqual((stats["uploaded"], stats["missing"], stats["unsupported"]), (2, 1, 1))
        self.assertEqual(uploaded, [])
        self.assertEqual(self.keys()[0], "data/00_raw/a/001.jpg")

    def test_uploads_updates_keys_and_is_idempotent(self) -> None:
        sid = self.scan.id
        stats, uploaded = self._run(dry_run=False, existing={f"gia-pha/{sid}/pages/002.png"})
        self.assertEqual((stats["uploaded"], stats["reused"]), (1, 1))
        self.assertEqual(uploaded, [(f"gia-pha/{sid}/pages/001.jpg", "001.jpg", "image/jpeg")])
        self.assertEqual(
            self.keys(),
            [f"gia-pha/{sid}/pages/001.jpg", f"gia-pha/{sid}/pages/002.png", "data/00_raw/a/003.jpg", "data/00_raw/a/004.pdf"],
        )
        stats, uploaded = self._run(dry_run=False)
        self.assertEqual((stats["already"], stats["uploaded"], uploaded), (2, 0, []))


class _PagesApi(_Pages):
    def setUp(self) -> None:
        super().setUp()
        self.db.add(User(email="o@x.l", full_name="O", password_hash="x", role=UserRole.USER))
        self.db.commit()
        self.user = self.owner
        api.app.dependency_overrides[get_db] = lambda: self.db
        api.app.dependency_overrides[get_current_user] = lambda: self.user
        api.app.dependency_overrides[require_workspace_database] = lambda: None
        storage = mock.Mock()
        storage.config.enabled = True
        storage.get_presigned_url.side_effect = lambda key: f"https://minio/{key}?sig"
        self.patch = mock.patch("app.documents.storage.ObjectStorage.from_env", return_value=storage)
        self.patch.start()
        self.client = TestClient(api.app)

    def tearDown(self) -> None:
        self.patch.stop()
        api.app.dependency_overrides.clear()
        super().tearDown()



class PagesEndpointTest(_PagesApi, unittest.TestCase):
    def test_lists_pages_with_text_and_signed_url_only_for_uploaded_images(self) -> None:
        page = GiaPhaPageRepository(self.db).list_by_scan(self.scan.id)[0]
        page.image_file_key = f"gia-pha/{self.scan.id}/pages/001.jpg"
        self.db.commit()
        body = self.client.get(f"/api/user/documents/{self.scan.id}/pages").json()
        self.assertEqual([p["page_number"] for p in body], [1, 2, 3, 4])
        self.assertEqual(body[0]["image_url"], f"https://minio/gia-pha/{self.scan.id}/pages/001.jpg?sig")
        self.assertIsNone(body[1]["image_url"])  # chưa upload → không đoán link
        self.assertEqual((body[0]["hannom_text"], body[0]["translation_text"]), ("漢1", "dịch 1"))

    def test_other_user_gets_404(self) -> None:
        self.user = self.db.query(User).filter_by(email="o@x.l").one()
        self.assertEqual(self.client.get(f"/api/user/documents/{self.scan.id}/pages").status_code, 404)

    def test_foreign_version_rejected(self) -> None:
        self.assertEqual(self.client.get(f"/api/user/documents/{self.scan.id}/pages?version_id=999").status_code, 404)


if __name__ == "__main__":
    unittest.main()


META = {
    "vote_method": "paddle_v6_backbone_line_vote_levenshtein_2_other",
    "engines": {"paddle_v6": {"text": "乾坤天", "score": 0.9, "similarity_to_others": 0.8}},
    "uncertain_rate": 0.5,
    "uncertain_spans": [
        {"line": 0, "voted_line": "乾坤天", "method": "line_no_majority", "n_agree": 1, "n_total": 3,
         "disagreeing": [{"engine": "gemini", "text": "乾坤夫", "similarity": 0.66}]}
    ],
    "structural_diffs": [],
}


class PageDetailEndpointTest(_PagesApi, unittest.TestCase):
    def setUp(self) -> None:
        super().setUp()
        page = GiaPhaPageRepository(self.db).list_by_scan(self.scan.id)[0]
        GiaPhaPageRepository(self.db).upsert_content(version_id=self.version.id, page_id=page.id, ocr_vote_meta=META)

    def test_page_detail_has_engines_and_annotated_vote(self) -> None:
        body = self.client.get(f"/api/user/documents/{self.scan.id}/pages/1").json()
        meta = body["ocr_vote_meta"]
        self.assertEqual(body["hannom_text"], "漢1")
        self.assertIn("paddle_v6", meta["engines"])
        span = meta["uncertain_spans"][0]
        self.assertEqual(span["voted_segments"][-1], {"text": "天", "contested": True})
        self.assertEqual(span["disagreeing"][0]["diff"][-1], {"op": "replace", "text": "夫"})

    def test_db_meta_is_not_mutated(self) -> None:
        self.client.get(f"/api/user/documents/{self.scan.id}/pages/1")
        self.db.expire_all()
        page = GiaPhaPageRepository(self.db).list_by_scan(self.scan.id)[0]
        stored = next(c for c in GiaPhaPageRepository(self.db).list_content_for_version(self.version.id) if c.page_id == page.id)
        self.assertNotIn("voted_segments", stored.ocr_vote_meta["uncertain_spans"][0])

    def test_page_without_vote_data(self) -> None:
        body = self.client.get(f"/api/user/documents/{self.scan.id}/pages/2").json()
        self.assertIsNone(body["ocr_vote_meta"])
        self.assertIsNone(body["ocr_bbox"])

    def test_page_detail_returns_bbox(self) -> None:
        boxes = [{"bbox_xyxy": [10, 20, 60, 900], "han": "乾坤天", "confidence": 0.97, "order": 1}]
        page = GiaPhaPageRepository(self.db).list_by_scan(self.scan.id)[0]
        GiaPhaPageRepository(self.db).upsert_content(version_id=self.version.id, page_id=page.id, ocr_bbox=boxes)
        body = self.client.get(f"/api/user/documents/{self.scan.id}/pages/1").json()
        self.assertEqual(body["ocr_bbox"], boxes)

    def test_missing_page_and_other_user(self) -> None:
        self.assertEqual(self.client.get(f"/api/user/documents/{self.scan.id}/pages/99").status_code, 404)
        self.user = self.db.query(User).filter_by(email="o@x.l").one()
        self.assertEqual(self.client.get(f"/api/user/documents/{self.scan.id}/pages/1").status_code, 404)


class PageDetailVoteV2Test(_PagesApi, unittest.TestCase):
    def test_v2_vote_meta_returned_as_is(self) -> None:
        from app.hannom.vote_char import build_vote_meta, vote_page

        lines = {"paddle_v6": ["先祖考王品"], "kim": ["先祖考三品"], "deepseek": ["先祖考三品"], "gv": ["先祖考三品"]}
        meta = build_vote_meta(vote_page(lines, ["paddle_v6"]), lines)
        page = GiaPhaPageRepository(self.db).list_by_scan(self.scan.id)[0]
        GiaPhaPageRepository(self.db).upsert_content(version_id=self.version.id, page_id=page.id, ocr_vote_meta=meta)
        body = self.client.get(f"/api/user/documents/{self.scan.id}/pages/1").json()
        got = body["ocr_vote_meta"]
        self.assertEqual((got["schema_version"], got["vote_method"]), (2, "char_majority"))
        self.assertEqual(got["slots"], meta["slots"])
        # Nền = engine giống đa số (đọc 三) → 三 giữ với 3 phiếu, phiếu 王 của Paddle vẫn lưu.
        slot = next(s for s in got["slots"] if s["index"] == 3)
        self.assertEqual((slot["status"], slot["final"], slot["votes"]["王"]), ("kept", "三", ["paddle_v6"]))
