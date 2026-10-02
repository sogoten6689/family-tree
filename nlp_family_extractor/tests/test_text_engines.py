import contextlib
import sys
import time
import unittest
from unittest import mock

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
from app.hannom import text_engine_runner, text_engines
from app.hannom.text_engine_runner import EngineJob, TextEngineRunner, fail_interrupted_runs
from app.workspace import models
from app.workspace.repository import GiaPhaPageRepository, GiaPhaVersionRepository, UserScanRepository
from app.workspace.router import require_workspace_database


@compiles(LONGTEXT, "sqlite")
def _longtext_as_sqlite_text(_type, _compiler, **_kw) -> str:
    return "TEXT"


def good_engine(text, *, page_number):
    return [{"cn": text[:2], "sv": f"âm {page_number}", "vi": f"nghĩa {page_number}"}]


class RegistryTest(unittest.TestCase):
    def setUp(self) -> None:
        self._saved = dict(text_engines.TEXT_ENGINE_REGISTRY)

    def tearDown(self) -> None:
        text_engines.TEXT_ENGINE_REGISTRY.clear()
        text_engines.TEXT_ENGINE_REGISTRY.update(self._saved)
        sys.modules.pop(text_engines.LOCAL_MODULE, None)

    def test_register_validates_name(self) -> None:
        with self.assertRaises(ValueError):
            text_engines.register_text_engine("Gemini Web", good_engine)
        text_engines.register_text_engine("gemini-web", good_engine)
        self.assertIn("gemini-web", text_engines.registered_engines())

    def test_enabled_defaults_to_all_and_filters_unknown(self) -> None:
        text_engines.TEXT_ENGINE_REGISTRY.clear()
        text_engines.register_text_engine("a", good_engine)
        text_engines.register_text_engine("b", good_engine)
        self.assertEqual(text_engines.enabled_engines(None), ["a", "b"])
        self.assertEqual(text_engines.enabled_engines("b,gone"), ["b"])

    def test_missing_local_module_is_not_an_error(self) -> None:
        self.assertIsNone(text_engines.load_local_engines())

    def test_broken_local_module_is_reported_not_raised(self) -> None:
        with mock.patch("importlib.import_module", side_effect=RuntimeError("boom")):
            error = text_engines.load_local_engines()
        self.assertIn("boom", error)
        self.assertEqual(text_engines.load_error(), error)


class _Db:
    """SQLite thật + session factory cho worker thread."""

    def __init__(self) -> None:
        self.engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
        Base.metadata.create_all(
            self.engine,
            tables=[
                User.__table__,
                models.UserScan.__table__,
                models.GiaPhaPage.__table__,
                models.GiaPhaVersion.__table__,
                models.GiaPhaVersionStep.__table__,
                models.GiaPhaPageContent.__table__,
            ],
        )

    @contextlib.contextmanager
    def session(self):
        db = Session(self.engine)
        try:
            yield db
            db.commit()
        finally:
            db.close()


class _Fixture:
    def setUp(self) -> None:
        self._saved = dict(text_engines.TEXT_ENGINE_REGISTRY)
        self.store = _Db()
        self.db = Session(self.store.engine)
        owner = User(email="o@t.l", full_name="O", password_hash="x", role=UserRole.USER)
        self.db.add(owner)
        self.db.commit()
        scan = UserScanRepository(self.db).create(user_id=owner.id, title="GP", file_name="a", file_type="pdf")
        self.scan_id = scan.id
        versions = GiaPhaVersionRepository(self.db)
        self.parent = versions.create_version(user_scan_id=scan.id, make_current=True)
        self.db.commit()
        pages = GiaPhaPageRepository(self.db)
        self.page_ids = {}
        for n, text in ((1, "乾坤天意"), (2, "家譜")):
            page = pages.create_page(user_scan_id=scan.id, page_number=n)
            self.page_ids[n] = page.id
            pages.upsert_content(version_id=self.parent.id, page_id=page.id, hannom_text=text, transliteration_text=f"KHN {n}")

    def tearDown(self) -> None:
        text_engines.TEXT_ENGINE_REGISTRY.clear()
        text_engines.TEXT_ENGINE_REGISTRY.update(self._saved)
        self.db.close()

    def _run(self, engine_fn, timeout=5.0):
        text_engines.register_text_engine("fake", engine_fn)
        versions = GiaPhaVersionRepository(self.db)
        version = versions.create_derived_version(
            user_scan_id=self.scan_id, parent_version_id=self.parent.id, source="engine-fake", review_status="approved"
        )
        runner = TextEngineRunner(session_factory=self.store.session, page_timeout=timeout)
        runner.submit(EngineJob(self.scan_id, version.id, "fake", [(1, "乾坤天意"), (2, "家譜")], self.page_ids))
        runner.wait_idle()
        self.db.expire_all()
        steps = {s.step_type.value: s for s in versions.steps_for(version.id)}
        contents = {c.page_id: c for c in GiaPhaPageRepository(self.db).list_content_for_version(version.id)}
        return versions.get(version.id), steps, contents


class RunnerTest(_Fixture, unittest.TestCase):
    def test_success_writes_pages_and_marks_done(self) -> None:
        version, steps, contents = self._run(good_engine)
        self.assertEqual(steps["transliteration"].status, "done")
        self.assertEqual(steps["translation"].status, "done")
        self.assertEqual(contents[self.page_ids[1]].transliteration_text, "âm 1")
        self.assertEqual(contents[self.page_ids[2]].translation_text, "nghĩa 2")
        self.assertEqual(contents[self.page_ids[1]].hannom_text, "乾坤天意")  # OCR giữ nguyên
        self.assertEqual(steps["ocr"].status, "pending")  # copy từ version cha
        self.assertIn("2 câu / 2 trang", version.note)
        self.assertEqual(version.review_status, "approved")
        parent_page1 = {c.page_id: c for c in GiaPhaPageRepository(self.db).list_content_for_version(self.parent.id)}
        self.assertEqual(parent_page1[self.page_ids[1]].transliteration_text, "KHN 1")

    def test_adapter_exception_marks_error_and_keeps_parent_text(self) -> None:
        def boom(text, *, page_number):
            raise RuntimeError("chưa đăng nhập")

        _, steps, contents = self._run(boom)
        self.assertEqual(steps["transliteration"].status, "error")
        self.assertIn("chưa đăng nhập", steps["translation"].error_message)
        self.assertEqual(contents[self.page_ids[1]].transliteration_text, "KHN 1")

    def test_timeout_marks_error(self) -> None:
        def slow(text, *, page_number):
            time.sleep(2)
            return []

        _, steps, _ = self._run(slow, timeout=0.2)
        self.assertEqual(steps["transliteration"].status, "error")
        self.assertIn("TimeoutError", steps["transliteration"].error_message)

    def test_invalid_output_rejected(self) -> None:
        _, steps, _ = self._run(lambda text, *, page_number: [{"cn": "乾", "sv": ""}])
        self.assertEqual(steps["translation"].status, "error")
        self.assertIn("thiếu", steps["translation"].error_message)

    def test_non_list_output_rejected(self) -> None:
        _, steps, _ = self._run(lambda text, *, page_number: "chuỗi")
        self.assertIn("phải trả về list", steps["translation"].error_message)

    def test_worker_survives_failure_and_runs_next_job(self) -> None:
        self._run(lambda text, *, page_number: 1 / 0)
        _, steps, _ = self._run(good_engine)
        self.assertEqual(steps["translation"].status, "done")

    def test_restart_marks_pending_and_running_as_error(self) -> None:
        versions = GiaPhaVersionRepository(self.db)
        stuck = versions.create_derived_version(
            user_scan_id=self.scan_id, parent_version_id=self.parent.id, source="engine-fake", review_status="approved"
        )
        imported = versions.create_derived_version(
            user_scan_id=self.scan_id,
            parent_version_id=self.parent.id,
            source="chatgpt-web",
            review_status="pending",
            text_step_status="pending",
        )
        self.assertEqual(fail_interrupted_runs(self.db), 2)  # 2 bước của version engine
        statuses = {s.step_type.value: s.status for s in versions.steps_for(stuck.id)}
        self.assertEqual((statuses["transliteration"], statuses["translation"]), ("error", "error"))
        untouched = {s.step_type.value: s.status for s in versions.steps_for(imported.id)}
        self.assertEqual(untouched["translation"], "pending")  # không đụng version không phải engine


class RunEndpointTest(_Fixture, unittest.TestCase):
    def setUp(self) -> None:
        super().setUp()
        text_engines.register_text_engine("fake", good_engine)
        self.other = User(email="x@t.l", full_name="X", password_hash="x", role=UserRole.USER)
        self.db.add(self.other)
        self.db.commit()
        self.user = self.db.get(User, 1)
        api.app.dependency_overrides[get_db] = lambda: self.db
        api.app.dependency_overrides[get_current_user] = lambda: self.user
        api.app.dependency_overrides[require_workspace_database] = lambda: None
        self.runner = TextEngineRunner(session_factory=self.store.session)
        self.patches = [
            mock.patch.object(text_engine_runner, "get_runner", return_value=self.runner),
            mock.patch("app.config._get_setting", return_value=None),
        ]
        for p in self.patches:
            p.start()
        self.client = TestClient(api.app)

    def tearDown(self) -> None:
        for p in self.patches:
            p.stop()
        api.app.dependency_overrides.clear()
        super().tearDown()

    def _post(self, **body):
        return self.client.post(f"/api/user/documents/{self.scan_id}/text-engine-runs", json={"engine": "fake", **body})

    def test_owner_runs_and_gets_pending_version_immediately(self) -> None:
        res = self._post()
        self.assertEqual(res.status_code, 200)
        body = res.json()
        self.assertEqual((body["source"], body["review_status"], body["is_current"]), ("engine-fake", "approved", False))
        self.runner.wait_idle()
        self.db.expire_all()
        steps = {s.step_type.value: s.status for s in GiaPhaVersionRepository(self.db).steps_for(body["version_id"])}
        self.assertEqual(steps["translation"], "done")

    def test_page_filter(self) -> None:
        version_id = self._post(pages=[2]).json()["version_id"]
        self.runner.wait_idle()
        self.db.expire_all()
        version = GiaPhaVersionRepository(self.db).get(version_id)
        self.assertIn("1 câu / 1 trang", version.note)

    def test_other_user_gets_404(self) -> None:
        self.user = self.other
        self.assertEqual(self._post().status_code, 404)

    def test_disabled_engine_rejected(self) -> None:
        with mock.patch("app.config._get_setting", return_value="someone-else"):
            self.assertEqual(self._post().status_code, 400)

    def test_unknown_engine_rejected(self) -> None:
        self.assertEqual(self._post(engine="nope").status_code, 400)

    def test_lists_enabled_engines(self) -> None:
        self.assertIn("fake", self.client.get("/api/user/text-engines").json())


if __name__ == "__main__":
    unittest.main()


class AdminTextEngineConfigTest(unittest.TestCase):
    def setUp(self) -> None:
        from app.auth.dependencies import require_admin

        self._saved = dict(text_engines.TEXT_ENGINE_REGISTRY)
        text_engines.TEXT_ENGINE_REGISTRY.clear()
        text_engines.register_text_engine("a", good_engine)
        text_engines.register_text_engine("b", good_engine)
        self.values: dict[str, str] = {}
        values = self.values

        class FakeStore:
            def get_value(self, _db, key):
                return values.get(key)

            def set_value(self, _db, key, value):
                values[key] = value

        api.app.dependency_overrides[require_admin] = lambda: object()
        api.app.dependency_overrides[get_db] = lambda: None
        self.patches = [
            mock.patch("app.settings.router.SettingsStore", FakeStore),
            mock.patch("app.settings.router.database_enabled", return_value=True),
        ]
        for p in self.patches:
            p.start()
        self.client = TestClient(api.app)

    def tearDown(self) -> None:
        for p in self.patches:
            p.stop()
        api.app.dependency_overrides.clear()
        text_engines.TEXT_ENGINE_REGISTRY.clear()
        text_engines.TEXT_ENGINE_REGISTRY.update(self._saved)

    def test_get_defaults_all_enabled(self) -> None:
        body = self.client.get("/api/admin/text-engines").json()
        self.assertEqual({e["name"]: e["enabled"] for e in body["engines"]}, {"a": True, "b": True})
        self.assertEqual(body["min_enabled"], 1)

    def test_cannot_disable_all(self) -> None:
        self.assertEqual(self.client.put("/api/admin/text-engines", json={"enabled": []}).status_code, 400)
        self.assertNotIn(text_engines.SETTING_KEY, self.values)

    def test_disable_one(self) -> None:
        res = self.client.put("/api/admin/text-engines", json={"enabled": ["b"]})
        self.assertEqual(res.status_code, 200)
        self.assertEqual(self.values[text_engines.SETTING_KEY], "b")
