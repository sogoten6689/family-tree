import unittest
from unittest import mock

from fastapi.testclient import TestClient

import api
from app.auth.dependencies import require_admin
from app.database import get_db
from app.hannom import engine_config
from app.hannom.engine_config import EngineConfigError, validate_enabled


class ValidateEnabledTest(unittest.TestCase):
    def test_rejects_empty(self) -> None:
        with self.assertRaises(EngineConfigError):
            validate_enabled([], ["kimhannom", "gemini_vision"])

    def test_rejects_blank_names_as_empty(self) -> None:
        with self.assertRaises(EngineConfigError):
            validate_enabled(["  ", ""], ["kimhannom"])

    def test_rejects_unknown_engine(self) -> None:
        with self.assertRaisesRegex(EngineConfigError, "paddle_v6"):
            validate_enabled(["kimhannom", "paddle_v6"], ["kimhannom"])

    def test_single_engine_allowed(self) -> None:
        self.assertEqual(validate_enabled(["gemini_vision"], ["kimhannom", "gemini_vision"]), ["gemini_vision"])

    def test_keeps_current_priority_order_and_dedupes(self) -> None:
        self.assertEqual(
            validate_enabled(["kimhannom", "gemini_vision", "kimhannom"], ["gemini_vision", "kimhannom"]),
            ["gemini_vision", "kimhannom"],
        )

    def test_newly_enabled_engine_appended_in_registry_order(self) -> None:
        self.assertEqual(validate_enabled(["gemini_vision", "kimhannom"], ["gemini_vision"]), ["gemini_vision", "kimhannom"])


class FakeStore:
    values: dict[str, str] = {}

    def get_value(self, _db, key):
        return self.values.get(key)

    def set_value(self, _db, key, value):
        self.values[key] = value


class OcrEnginesEndpointTest(unittest.TestCase):
    def setUp(self) -> None:
        FakeStore.values = {}
        api.app.dependency_overrides[require_admin] = lambda: object()
        api.app.dependency_overrides[get_db] = lambda: None
        self.patches = [
            mock.patch("app.settings.router.SettingsStore", FakeStore),
            mock.patch("app.settings.router.database_enabled", return_value=True),
            mock.patch.object(engine_config, "engine_ready", return_value=(True, None)),
        ]
        for p in self.patches:
            p.start()
        self.client = TestClient(api.app)

    def tearDown(self) -> None:
        for p in self.patches:
            p.stop()
        api.app.dependency_overrides.clear()

    def test_get_defaults_to_both_engines_enabled(self) -> None:
        with mock.patch("app.config._get_setting", return_value=None):
            body = self.client.get("/api/admin/ocr-engines").json()
        self.assertEqual(body["min_enabled"], 1)
        self.assertEqual({e["name"]: e["enabled"] for e in body["engines"]}, {"kimhannom": True, "gemini_vision": True})

    def test_put_disables_one_engine_and_persists_setting(self) -> None:
        res = self.client.put("/api/admin/ocr-engines", json={"enabled": ["kimhannom"]})
        self.assertEqual(res.status_code, 200)
        self.assertEqual(FakeStore.values["HANNOM_VOTE_ENGINES"], "kimhannom")
        self.assertEqual({e["name"]: e["enabled"] for e in res.json()["engines"]}, {"kimhannom": True, "gemini_vision": False})

    def test_put_rejects_disabling_all(self) -> None:
        FakeStore.values = {"HANNOM_VOTE_ENGINES": "kimhannom"}
        res = self.client.put("/api/admin/ocr-engines", json={"enabled": []})
        self.assertEqual(res.status_code, 400)
        self.assertEqual(FakeStore.values["HANNOM_VOTE_ENGINES"], "kimhannom")  # không bị ghi đè

    def test_put_rejects_unknown_engine(self) -> None:
        res = self.client.put("/api/admin/ocr-engines", json={"enabled": ["nope"]})
        self.assertEqual(res.status_code, 400)
        self.assertNotIn("HANNOM_VOTE_ENGINES", FakeStore.values)


class PipelineEngineGuardTest(unittest.TestCase):
    def test_no_valid_engine_raises_clear_error_before_any_ocr_call(self) -> None:
        from app.hannom.errors import HannomApiError
        from app.hannom.pipeline import process_hannom_image_v2

        with mock.patch("app.config.get_hannom_vote_engines", return_value=["typo_engine"]):
            with self.assertRaisesRegex(HannomApiError, "typo_engine"):
                process_hannom_image_v2(b"img", "a.png")


if __name__ == "__main__":
    unittest.main()
