import os
import unittest

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


if __name__ == "__main__":
    unittest.main()
