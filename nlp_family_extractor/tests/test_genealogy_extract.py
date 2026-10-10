import unittest

from fastapi.testclient import TestClient

import api

VI = "Nguyễn Văn An sinh năm 1945. Nguyễn Văn An kết hôn với bà Trần Thị Hạnh. Nguyễn Văn Bình là con của Nguyễn Văn An."


class GenealogyExtractEndpointTest(unittest.TestCase):
    def setUp(self) -> None:
        self.client = TestClient(api.app)

    def post(self, text=VI, language="vietnamese", model_version="regex"):
        return self.client.post("/api/genealogy/extract", json={"text": text, "language": language, "model_version": model_version})

    def test_regex_vietnamese_works_and_merges_duplicate_mentions(self) -> None:
        body = self.post().json()
        self.assertTrue(body["success"], body.get("error"))
        data = body["data"]
        self.assertIn("Nguyễn Văn An", data["persons"])
        self.assertEqual(len(data["persons"]), len(set(data["persons"])))  # không trùng tên
        self.assertEqual(data["person_years"]["Nguyễn Văn An"], 1945)
        self.assertEqual(data["statistics"], {"person_count": len(data["persons"]), "relation_count": len(data["relations"])})
        self.assertTrue(all({"head", "type", "tail", "confidence"} <= set(r) for r in data["relations"]))
        triples = [(r["head"], r["type"], r["tail"]) for r in data["relations"]]
        self.assertEqual(len(triples), len(set(triples)))  # không trùng quan hệ
        self.assertTrue(all(h != t for h, _, t in triples))
        self.assertEqual(data["model_info"]["model_name"], "FamilyExtractor-Regex-MVP")

    def test_untrained_models_are_refused_instead_of_faking_a_label(self) -> None:
        for version in ("phobert", "sikubert"):
            body = self.post(model_version=version).json()
            self.assertFalse(body["success"])
            self.assertIn("chưa được huấn luyện", body["error"])
            self.assertIsNone(body["data"])

    def test_hannom_is_refused_by_the_vietnamese_rule_extractor(self) -> None:
        body = self.post(text="始祖清閑公配陳氏生子敏達", language="hannom").json()
        self.assertFalse(body["success"])
        self.assertIn("Hán-Nôm", body["error"])

    def test_empty_text_is_a_400(self) -> None:
        self.assertEqual(self.post(text="   ").status_code, 400)

    def test_invalid_enums_are_422(self) -> None:
        self.assertEqual(self.post(language="klingon").status_code, 422)
        self.assertEqual(self.post(model_version="gpt").status_code, 422)


if __name__ == "__main__":
    unittest.main()
