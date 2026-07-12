import unittest

from app.balkan_node import (
    build_canonical_node,
    extract_node_meta,
    strip_nodes_and_collect_meta,
)
from app.export.service import ExportFormat, FamilyTreeExportService


class BalkanNodeTest(unittest.TestCase):
    def test_strip_detail_into_meta(self) -> None:
        raw = [
            {
                "id": 1,
                "name": "Nguyễn Văn A",
                "gender": "male",
                "detail": {"display_name": "Nguyễn Văn A", "note": "ghi chú"},
                "burialPlace": "Hà Nội",
            }
        ]
        nodes, meta = strip_nodes_and_collect_meta(raw)
        self.assertEqual(nodes[0]["name"], "Nguyễn Văn A")
        self.assertNotIn("detail", nodes[0])
        self.assertIn(1, meta)
        self.assertEqual(meta[1]["burialPlace"], "Hà Nội")

    def test_build_canonical_strips_unknown_fields(self) -> None:
        node = build_canonical_node(
            {"id": 2, "name": "Test", "gender": "female", "extra": "drop"},
            node_id=2,
        )
        self.assertNotIn("extra", node)

    def test_extract_node_meta_empty(self) -> None:
        self.assertIsNone(extract_node_meta({"id": 1, "name": "A", "gender": "male"}))


class ExportServiceTest(unittest.TestCase):
    def setUp(self) -> None:
        self.doc = {
            "id": "tree-test",
            "name": "Họ Nguyễn",
            "nodes": [
                {
                    "id": 1,
                    "name": "Nguyễn Văn A",
                    "gender": "male",
                    "birthYear": 1880,
                    "bio": "Ghi chú tiếng Việt",
                },
                {
                    "id": 2,
                    "name": "Nguyễn Thị B",
                    "gender": "female",
                    "pids": [1],
                    "fid": 1,
                },
            ],
        }
        self.service = FamilyTreeExportService()

    def test_gedcom_utf8_header(self) -> None:
        content, filename, media_type = self.service.export(self.doc, ExportFormat.GEDCOM)
        self.assertTrue(filename.endswith(".ged"))
        self.assertIn("CHAR UTF-8", content)
        self.assertIn("Nguyễn Văn A", content)
        self.assertIn("charset=utf-8", media_type)

    def test_csv_utf8_bom(self) -> None:
        content, filename, _ = self.service.export(self.doc, ExportFormat.CSV)
        self.assertTrue(filename.endswith(".csv"))
        self.assertTrue(content.startswith("\ufeff"))
        self.assertIn("Nguyễn Văn A", content)

    def test_json_export(self) -> None:
        content, filename, _ = self.service.export(self.doc, ExportFormat.JSON)
        self.assertTrue(filename.endswith(".json"))
        self.assertIn('"nodes"', content)


if __name__ == "__main__":
    unittest.main()
