import json
import os
import tempfile
import unittest
from pathlib import Path

from fastapi.testclient import TestClient

import api
from app.doi_chieu import service

MACHINE = """id,trang,dong,han,viet_may,viet_sua,trang_thai,ghi_chu,align_method,confidence
a:001:001,001,1,公回改性名避之其後明人,ông về đổi họ tên tránh đi về sau người Minh,,,,,
a:001:002,001,2,設立學校以牧人才,lập trường học để thu nhân tài,,,,,
a:002:001,002,1,脫軒詠詩云上庠琴劍,Thoát Hiên vịnh thơ rằng,,,,,
"""

TSV = (
    "公回，改姓名避之。\tÔng trở về, đổi họ tên để lánh đi.\n"
    "其後明人設立學校以收人才。\tVề sau người Minh lập trường học để thu nạp nhân tài.\n"
    "dòng không có tab\n"
    "公回，改姓名避之。\tÔng trở về, đổi họ tên để lánh đi.\n"
    "漢\t越 lẫn 字\n"
)


class ParseTsvTest(unittest.TestCase):
    def test_format_errors(self) -> None:
        pairs = service.parse_tsv("﻿" + TSV)
        self.assertEqual([p.errors for p in pairs[:2]], [[], []])
        self.assertIn("có 0 tab, cần đúng 1", pairs[2].errors)
        self.assertIn("trùng dòng 1", pairs[3].errors)
        self.assertIn("vế Việt lẫn chữ Hán", pairs[4].errors)
        self.assertIn("thiếu một vế", service.parse_tsv("漢\t\n")[0].errors)
        self.assertIn("vế Hán không có chữ Hán", service.parse_tsv("abc\tdef\n")[0].errors)

    def test_slug_rejects_traversal(self) -> None:
        for bad in ["..", "../x", "a/b", "", ".hidden"]:
            self.assertFalse(service.is_slug(bad), bad)
        self.assertTrue(service.is_slug("nom-833"))


class DoiChieuApiTest(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        root = Path(self.tmp.name)
        book = root / "sv-a" / "nom-1"
        (book / "anh").mkdir(parents=True)
        (root / "sv-a" / "meta.json").write_text(json.dumps({"ten": "Sinh viên A"}), encoding="utf-8")
        (book / "cap_cau.csv").write_text(MACHINE, encoding="utf-8")
        (book / "nom-1_parallel.tsv").write_text(TSV, encoding="utf-8")
        (book / "anh" / "001.jpg").write_bytes(b"\xff\xd8jpg")
        catalogue = {"nom-1": {"ten": "Cuốn một", "link": "https://drive.google.com/file/d/x/view"}, "nom-2": {"link": "javascript:x"}}
        (root / "danh_muc.json").write_text(json.dumps(catalogue), encoding="utf-8")
        self.old = os.environ.get("DOI_CHIEU_DIR")
        os.environ["DOI_CHIEU_DIR"] = str(root)
        self.client = TestClient(api.app)

    def tearDown(self) -> None:
        if self.old is None:
            os.environ.pop("DOI_CHIEU_DIR", None)
        else:
            os.environ["DOI_CHIEU_DIR"] = self.old
        self.tmp.cleanup()

    def test_overview_counts_valid_pairs(self) -> None:
        body = self.client.get("/api/public/doi-chieu").json()
        self.assertEqual(body["target"], 2000)
        (student,) = body["students"]
        self.assertEqual((student["ten"], student["pairs"], student["valid"]), ("Sinh viên A", 5, 2))
        self.assertEqual(student["books"][0]["machine_pages"], 2)
        self.assertEqual(student["books"][0]["ten"], "Cuốn một")
        self.assertTrue(student["books"][0]["link"].startswith("https://drive.google.com/"))

    def test_catalogue_drops_non_https_links(self) -> None:
        cat = service.catalogue(Path(os.environ["DOI_CHIEU_DIR"]))
        self.assertIsNone(cat["nom-2"]["link"])
        self.assertEqual(service.book_info(Path(os.environ["DOI_CHIEU_DIR"]), "khong-co"), {"ten": None, "link": None})

    def test_book_links_machine_rows_by_han(self) -> None:
        body = self.client.get("/api/public/doi-chieu/sv-a/nom-1").json()
        self.assertEqual(body["ten"], "Cuốn một")
        first, second = body["pairs"][:2]
        self.assertEqual(first["trang"], ["001"])
        self.assertIn("ông về", first["may_viet"])
        self.assertIn("lập trường học", second["may_viet"])
        self.assertGreater(second["coverage"], 0.5)
        # Cột trang 002 không cặp nào phủ tới → ứng viên thiếu.
        self.assertEqual([m["trang"] for m in body["missing"]], ["002"])

    def test_image_and_bad_paths(self) -> None:
        self.assertEqual(self.client.get("/api/public/doi-chieu/sv-a/nom-1/anh/001").status_code, 200)
        self.assertEqual(self.client.get("/api/public/doi-chieu/sv-a/nom-1/anh/999").status_code, 404)
        self.assertEqual(self.client.get("/api/public/doi-chieu/sv-a/%2e%2e").status_code, 404)
        self.assertEqual(self.client.get("/api/public/doi-chieu/sv-a/khong-co").status_code, 404)

    def test_no_data_dir_returns_empty(self) -> None:
        os.environ["DOI_CHIEU_DIR"] = str(Path(self.tmp.name) / "khong-ton-tai")
        self.assertEqual(self.client.get("/api/public/doi-chieu").json()["students"], [])
