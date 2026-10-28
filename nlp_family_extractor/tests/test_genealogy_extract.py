import os
import unittest
from unittest import mock

from fastapi.testclient import TestClient

import api

VI = "Ông Nguyễn Văn An sinh năm 1945, quê ở làng Bình Hòa."


class GenealogyExtractEndpointTest(unittest.TestCase):
    def setUp(self) -> None:
        self.client = TestClient(api.app)

    def post(self, text=VI, language="vietnamese", model_version="ner"):
        return self.client.post("/api/genealogy/extract", json={"text": text, "language": language, "model_version": model_version})

    def test_regex_is_gone_422(self) -> None:
        self.assertEqual(self.post(model_version="regex").status_code, 422)

    def test_default_is_ner_and_requires_deployed_model(self) -> None:
        os.environ.pop("NER_MODEL_DIR_VI", None)
        r = self.client.post("/api/genealogy/extract", json={"text": VI}).json()  # không gửi model_version
        self.assertFalse(r["success"])
        self.assertIn("chưa sẵn sàng", r["error"])

    def test_legacy_phobert_alias_still_accepted(self) -> None:
        os.environ.pop("NER_MODEL_DIR_VI", None)
        self.assertIn("chưa sẵn sàng", self.post(model_version="phobert").json()["error"])

    def test_sikubert_and_hannom_refused_without_han_model(self) -> None:
        os.environ.pop("NER_MODEL_DIR_HAN", None)
        for body in (self.post(model_version="sikubert").json(), self.post(text="始祖清閑公配陳氏生子敏達", language="hannom").json()):
            self.assertFalse(body["success"])
            self.assertIn("chữ Hán", body["error"])
            self.assertIn("NER_MODEL_DIR_HAN", body["error"])
            self.assertIsNone(body["data"])

    def test_empty_text_is_a_400(self) -> None:
        self.assertEqual(self.post(text="   ").status_code, 400)

    def test_invalid_enums_are_422(self) -> None:
        self.assertEqual(self.post(language="klingon").status_code, 422)
        self.assertEqual(self.post(model_version="gpt").status_code, 422)


class _FakeModel:
    def __init__(self, info=None):
        self.info = info or {}

    def extract(self, text):
        return [{"label": "PER_NAME", "text": "An", "start": 0, "end": 2, "confidence": 0.9}]


class GenealogyExtractPipelineTest(unittest.TestCase):
    """Tham số ``pipeline`` (SPEC §0) — model giả, không cần ONNX."""

    def setUp(self) -> None:
        self.client = TestClient(api.app)
        self.calls = []

        def fake_get(language="vi"):
            self.calls.append(language)
            return _FakeModel(self.card)

        self.card = {}
        patcher = mock.patch("app.ner.get_ner_model", side_effect=fake_get)
        patcher.start()
        self.addCleanup(patcher.stop)
        for key in ("NER_MODEL_NAME_VI", "NER_MODEL_NAME_HAN"):
            self.addCleanup(os.environ.pop, key, None)
            os.environ.pop(key, None)

    def post(self, **body):
        return self.client.post("/api/genealogy/extract", json={"text": VI, **body})

    def test_pipeline_vi_returns_xlmr_family(self) -> None:
        r = self.post(pipeline="vi").json()
        self.assertTrue(r["success"])
        self.assertEqual(self.calls, ["vi"])
        info = r["data"]["model_info"]
        self.assertEqual((info["name"], info["pipeline"], info["language"]), ("xlmr-family", "vi", "vietnamese"))
        self.assertEqual(r["data"]["relations"], [])
        self.assertIn("chưa có quan hệ", info["note"])

    def test_pipeline_han_returns_sikubert_family(self) -> None:
        info = self.post(pipeline="han").json()["data"]["model_info"]
        self.assertEqual(self.calls, ["han"])
        self.assertEqual((info["name"], info["pipeline"], info["language"]), ("sikubert-family", "han", "hannom"))

    def test_pipeline_overrides_language_and_model_version(self) -> None:
        self.post(pipeline="vi", language="hannom", model_version="sikubert")
        self.post(pipeline="han", language="vietnamese", model_version="ner")
        self.assertEqual(self.calls, ["vi", "han"])

    def test_without_pipeline_old_clients_resolve_as_before(self) -> None:
        cases = [({}, "vi"), ({"model_version": "ner"}, "vi"), ({"model_version": "phobert"}, "vi"),
                 ({"model_version": "sikubert"}, "han"), ({"language": "hannom"}, "han")]
        for body, expected in cases:
            info = self.post(**body).json()["data"]["model_info"]
            self.assertEqual(info["pipeline"], expected, body)
            self.assertEqual(info["name"], api._PIPELINE_MODEL_NAMES[expected], body)

    def test_unknown_pipeline_is_422_and_never_runs_a_model(self) -> None:
        for bad in ("klingon", "VI", "", "xlmr-family"):
            self.assertEqual(self.post(pipeline=bad).status_code, 422, bad)
        self.assertEqual(self.calls, [])

    def test_name_comes_from_env_then_model_card(self) -> None:
        self.card = {"name": "xlmr-family-v2"}
        self.assertEqual(self.post(pipeline="vi").json()["data"]["model_info"]["name"], "xlmr-family-v2")
        os.environ["NER_MODEL_NAME_VI"] = "xlmr-family-prod"
        self.assertEqual(self.post(pipeline="vi").json()["data"]["model_info"]["name"], "xlmr-family-prod")

    def test_unavailable_model_reports_error_for_pipeline(self) -> None:
        from app.ner import NerUnavailable

        with mock.patch("app.ner.get_ner_model", side_effect=NerUnavailable("Chưa cấu hình NER_MODEL_DIR_HAN")):
            r = self.post(pipeline="han").json()
        self.assertFalse(r["success"])
        self.assertIn("NER_MODEL_DIR_HAN", r["error"])


if __name__ == "__main__":
    unittest.main()
