import unittest

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.dialects.mysql import LONGTEXT
from sqlalchemy.ext.compiler import compiles
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

import api
from app.auth.dependencies import get_current_user
from app.auth.models import User, UserRole
from app.database import Base, get_db
from app.workspace import models
from app.workspace.llm_import import cn_coverage, parse_import
from app.workspace.repository import GiaPhaPageRepository, GiaPhaVersionRepository, UserScanRepository
from app.workspace.router import require_workspace_database


@compiles(LONGTEXT, "sqlite")
def _longtext_as_sqlite_text(_type, _compiler, **_kw) -> str:
    return "TEXT"


def rec(page=1, cn="乾坤天意", sv="Càn khôn thiên ý", vi="Ý trời đất"):
    return {"page": page, "cn": cn, "sv": sv, "vi": vi}


class ParseImportTest(unittest.TestCase):
    def test_valid_payload(self) -> None:
        parsed = parse_import({"source": "chatgpt-web", "records": [rec(1), rec(2)]}, {1, 2})
        self.assertEqual(parsed.errors, [])
        self.assertEqual(parsed.record_count, 2)

    def test_rejects_bad_source(self) -> None:
        self.assertTrue(parse_import({"source": "ChatGPT Web!", "records": [rec()]}, {1}).errors)

    def test_rejects_missing_fields_and_unknown_page(self) -> None:
        parsed = parse_import({"source": "x", "records": [rec(sv=""), rec(page=9), {"page": "1"}]}, {1})
        self.assertEqual(len(parsed.errors), 3)
        self.assertIn("thiếu sv", parsed.errors[0])
        self.assertIn("trang 9", parsed.errors[1])

    def test_rejects_bool_page(self) -> None:
        self.assertTrue(parse_import({"source": "x", "records": [rec(page=True)]}, {1}).errors)

    def test_skips_annotations(self) -> None:
        parsed = parse_import({"source": "x", "records": [rec(), rec(vi="[Chú giải] ghi chú")]}, {1})
        self.assertEqual((parsed.record_count, parsed.skipped_annotations), (1, 1))

    def test_only_annotations_is_an_error(self) -> None:
        self.assertTrue(parse_import({"source": "x", "records": [rec(cn="[Chú giải]")]}, {1}).errors)


class CoverageTest(unittest.TestCase):
    def test_full_match_ignores_punctuation_and_spaces(self) -> None:
        self.assertEqual(cn_coverage(["乾坤，天意"], "乾 坤 天 意 愛"), 1.0)

    def test_counts_multiplicity(self) -> None:
        self.assertEqual(cn_coverage(["天天"], "天"), 0.5)

    def test_non_bmp(self) -> None:
        self.assertEqual(cn_coverage(["𠀀家"], "𠀀"), 0.5)

    def test_no_ocr(self) -> None:
        self.assertIsNone(cn_coverage(["天"], None))


class ImportEndpointTest(unittest.TestCase):
    """Chạy endpoint thật trên SQLite: phân quyền, version cũ giữ nguyên,
    duyệt không đổi version hiện tại, export chỉ lấy bản đã duyệt."""

    def setUp(self) -> None:
        engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
        Base.metadata.create_all(
            engine,
            tables=[
                User.__table__,
                models.UserScan.__table__,
                models.GiaPhaPage.__table__,
                models.GiaPhaVersion.__table__,
                models.GiaPhaVersionStep.__table__,
                models.GiaPhaPageContent.__table__,
            ],
        )
        self.db = Session(engine)
        self.owner = User(email="o@t.l", full_name="O", password_hash="x", role=UserRole.USER)
        self.other = User(email="x@t.l", full_name="X", password_hash="x", role=UserRole.USER)
        self.admin = User(email="a@t.l", full_name="A", password_hash="x", role=UserRole.ADMIN)
        self.db.add_all([self.owner, self.other, self.admin])
        self.db.commit()
        scan = UserScanRepository(self.db).create(user_id=self.owner.id, title="GP", file_name="a.pdf", file_type="pdf")
        self.scan_id = scan.id
        pages = GiaPhaPageRepository(self.db)
        versions = GiaPhaVersionRepository(self.db)
        self.v1 = versions.create_version(user_scan_id=scan.id, make_current=True)
        self.db.commit()
        for number, ocr in ((1, "乾坤天意愛維新"), (2, "家譜")):
            page = pages.create_page(user_scan_id=scan.id, page_number=number)
            pages.upsert_content(
                version_id=self.v1.id, page_id=page.id, hannom_text=ocr, transliteration_text=f"KHN {number}"
            )

        self.user = self.owner
        api.app.dependency_overrides[get_db] = lambda: self.db
        api.app.dependency_overrides[get_current_user] = lambda: self.user
        api.app.dependency_overrides[require_workspace_database] = lambda: None
        self.client = TestClient(api.app)

    def tearDown(self) -> None:
        api.app.dependency_overrides.clear()
        self.db.close()

    def _import(self, records, dry_run=False):
        return self.client.post(
            f"/api/user/documents/{self.scan_id}/imports",
            json={"source": "chatgpt-web", "model_note": "GPT-4o", "records": records, "dry_run": dry_run},
        )

    def test_dry_run_creates_nothing_and_warns_on_low_coverage(self) -> None:
        res = self._import([rec(1), rec(2, cn="完全不同")], dry_run=True)
        body = res.json()
        self.assertEqual(res.status_code, 200)
        self.assertTrue(body["ok"])
        self.assertIsNone(body["version"])
        self.assertTrue(any("Trang 2" in w for w in body["warnings"]))
        self.assertFalse(any("Trang 1" in w for w in body["warnings"]))
        self.assertEqual(len(GiaPhaVersionRepository(self.db).list_by_scan(self.scan_id)), 1)

    def test_import_creates_pending_version_and_keeps_parent(self) -> None:
        res = self._import([rec(1), rec(1, cn="愛維新", sv="Ái duy tân", vi="Yêu đổi mới")])
        self.assertEqual(res.status_code, 200)
        version = res.json()["version"]
        self.assertEqual((version["source"], version["review_status"], version["is_current"]), ("chatgpt-web", "pending", False))
        self.assertEqual(version["parent_version_id"], self.v1.id)

        pages = GiaPhaPageRepository(self.db)
        new = {c.page_id: c for c in pages.list_content_for_version(version["version_id"])}
        old = {c.page_id: c for c in pages.list_content_for_version(self.v1.id)}
        page1 = min(old)
        self.assertEqual(new[page1].transliteration_text, "Càn khôn thiên ý\nÁi duy tân")
        self.assertEqual(new[page1].hannom_text, "乾坤天意愛維新")  # giữ OCR của version cha
        self.assertEqual(len(new[page1].pairs), 2)
        self.assertEqual(old[page1].transliteration_text, "KHN 1")  # version cha không đổi
        page2 = max(old)
        self.assertEqual(new[page2].transliteration_text, "KHN 2")  # trang không nhập: copy từ cha
        self.assertIsNone(new[page2].pairs)

    def test_invalid_import_is_rejected(self) -> None:
        res = self._import([rec(page=5)])
        self.assertEqual(res.status_code, 400)
        self.assertEqual(len(GiaPhaVersionRepository(self.db).list_by_scan(self.scan_id)), 1)

    def test_other_user_cannot_import(self) -> None:
        self.user = self.other
        self.assertEqual(self._import([rec()]).status_code, 404)

    def test_admin_can_import(self) -> None:
        self.user = self.admin
        self.assertEqual(self._import([rec()]).status_code, 200)

    def test_review_is_admin_only_and_does_not_change_current(self) -> None:
        version_id = self._import([rec()]).json()["version"]["version_id"]
        url = f"/api/user/documents/{self.scan_id}/versions/{version_id}/review"
        self.assertEqual(self.client.patch(url, json={"review_status": "approved"}).status_code, 403)
        self.user = self.admin
        res = self.client.patch(url, json={"review_status": "approved"})
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.json()["review_status"], "approved")
        self.assertFalse(res.json()["is_current"])
        self.assertEqual(GiaPhaVersionRepository(self.db).get_current(self.scan_id).id, self.v1.id)

    def test_make_current_is_admin_only_and_syncs_flat_cache(self) -> None:
        version_id = self._import([rec()]).json()["version"]["version_id"]
        url = f"/api/user/documents/{self.scan_id}/versions/{version_id}/make-current"
        self.assertEqual(self.client.post(url).status_code, 403)  # chủ bộ (không phải admin)
        self.user = self.admin
        res = self.client.post(url)
        self.assertEqual(res.status_code, 200)
        self.assertTrue(res.json()["is_current"])
        versions = GiaPhaVersionRepository(self.db)
        self.assertEqual(versions.get_current(self.scan_id).id, version_id)
        self.assertEqual(len(versions.list_by_scan(self.scan_id)), 2)  # không tạo bản sao
        scan = UserScanRepository(self.db).get(self.scan_id)
        self.db.refresh(scan)
        self.assertIn("Càn khôn thiên ý", scan.transliteration_text)  # cache phẳng theo version mới
        self.assertEqual(self.client.post(url.replace(str(version_id), "999")).status_code, 404)

    def test_make_current_rejects_unfinished_engine_version(self) -> None:
        versions = GiaPhaVersionRepository(self.db)
        engine_version = versions.create_derived_version(
            user_scan_id=self.scan_id, parent_version_id=self.v1.id, source="engine-kim_gemini", review_status="approved"
        )
        self.user = self.admin
        res = self.client.post(f"/api/user/documents/{self.scan_id}/versions/{engine_version.id}/make-current")
        self.assertEqual(res.status_code, 400)
        self.assertEqual(versions.get_current(self.scan_id).id, self.v1.id)

    def test_cannot_review_pipeline_version(self) -> None:
        self.user = self.admin
        res = self.client.patch(
            f"/api/user/documents/{self.scan_id}/versions/{self.v1.id}/review", json={"review_status": "approved"}
        )
        self.assertEqual(res.status_code, 400)

    def test_export_contains_only_approved_pairs(self) -> None:
        approved = self._import([rec(1)]).json()["version"]["version_id"]
        self._import([rec(1, sv="khác")])  # vẫn pending
        self.user = self.admin
        self.client.patch(
            f"/api/user/documents/{self.scan_id}/versions/{approved}/review", json={"review_status": "approved"}
        )
        lines = self.client.get("/api/admin/training-export").text.strip().splitlines()
        self.assertEqual(len(lines), 1)
        self.assertIn('"sv": "Càn khôn thiên ý"', lines[0])
        self.assertIn('"source": "chatgpt-web"', lines[0])

    def test_clone_keeps_pairs(self) -> None:
        version_id = self._import([rec(1)]).json()["version"]["version_id"]
        clone = GiaPhaVersionRepository(self.db).clone_version(version_id)
        contents = GiaPhaPageRepository(self.db).list_content_for_version(clone.id)
        self.assertTrue(any(c.pairs for c in contents))


if __name__ == "__main__":
    unittest.main()
