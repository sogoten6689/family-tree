import json
import os
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

from fastapi.testclient import TestClient

import api
from app.auth.dependencies import get_current_user
from app.auth.models import UserRole
from app.database import get_db
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
        self.assertEqual(student["books"][0]["image_pages"], 1)
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

    def test_book_without_machine_lists_images(self) -> None:
        anh = Path(os.environ["DOI_CHIEU_DIR"]) / "sv-a" / "hxh-1" / "anh"
        anh.mkdir(parents=True)
        for name in ["002.jpg", "001.png", "ghi_chu.txt"]:
            (anh / name).write_bytes(b"x")
        body = self.client.get("/api/public/doi-chieu/sv-a/hxh-1").json()
        self.assertEqual((body["pages"], body["stats"]["machine_rows"]), (["001", "002"], 0))

    def test_image_and_bad_paths(self) -> None:
        self.assertEqual(self.client.get("/api/public/doi-chieu/sv-a/nom-1/anh/001").status_code, 200)
        self.assertEqual(self.client.get("/api/public/doi-chieu/sv-a/nom-1/anh/999").status_code, 404)
        self.assertEqual(self.client.get("/api/public/doi-chieu/sv-a/%2e%2e").status_code, 404)
        self.assertEqual(self.client.get("/api/public/doi-chieu/sv-a/khong-co").status_code, 404)

    def test_no_data_dir_returns_empty(self) -> None:
        os.environ["DOI_CHIEU_DIR"] = str(Path(self.tmp.name) / "khong-ton-tai")
        self.assertEqual(self.client.get("/api/public/doi-chieu").json()["students"], [])


class SoatApiTest(unittest.TestCase):
    URL = "/api/doi-chieu/sv-a/nom-1/soat"

    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.book = Path(self.tmp.name) / "sv-a" / "nom-1"
        self.book.mkdir(parents=True)
        (self.book / "cap_cau.csv").write_text(MACHINE, encoding="utf-8")
        self.old = os.environ.get("DOI_CHIEU_DIR")
        os.environ["DOI_CHIEU_DIR"] = self.tmp.name
        api.app.dependency_overrides[get_db] = lambda: None
        self.client = TestClient(api.app)
        self.login(UserRole.ADMIN)

    def tearDown(self) -> None:
        api.app.dependency_overrides.clear()
        if self.old is None:
            os.environ.pop("DOI_CHIEU_DIR", None)
        else:
            os.environ["DOI_CHIEU_DIR"] = self.old
        self.tmp.cleanup()

    def login(self, role: UserRole) -> None:
        user = SimpleNamespace(role=role, email="nguoi-soat@example.test")
        api.app.dependency_overrides[get_current_user] = lambda: user

    def save(self, rows: list[dict], da_soat: list[str], phien_ban: int = 0):
        return self.client.put(self.URL, json={"rows": rows, "da_soat": da_soat, "phien_ban": phien_ban})

    @staticmethod
    def row(trang: str, han: str, viet: str, bo: bool = False) -> dict:
        return {"trang": trang, "han": han, "viet": viet, "bo": bo}

    def valid_count(self) -> int:
        return self.client.get("/api/public/doi-chieu/sv-a/nom-1").json()["stats"]["valid"]

    def test_requires_admin(self) -> None:
        api.app.dependency_overrides.pop(get_current_user)
        self.assertEqual(self.client.get(self.URL).status_code, 401)
        self.assertEqual(self.client.post(f"{self.URL}/nop").status_code, 401)
        self.login(UserRole.USER)
        self.assertEqual(self.client.get(self.URL).status_code, 403)
        self.assertEqual(self.save([], []).status_code, 403)
        self.assertEqual(self.client.post(f"{self.URL}/nop").status_code, 403)
        self.assertFalse((self.book / "soat_nhap.json").exists())

    def test_first_load_comes_from_machine_rows(self) -> None:
        body = self.client.get(self.URL).json()
        self.assertEqual(body["phien_ban"], 0)
        self.assertEqual(body["da_soat"], [])
        self.assertEqual(len(body["rows"]), 3)
        self.assertEqual(body["rows"][0]["viet"], "ông về đổi họ tên tránh đi về sau người Minh")

    def test_draft_does_not_count_until_submitted(self) -> None:
        saved = self.save([self.row("001", "公回。", "Ông về.")], ["001"]).json()
        self.assertEqual((saved["phien_ban"], saved["nguoi_soat"]), (1, "nguoi-soat@example.test"))
        self.assertEqual(self.client.get(self.URL).json()["rows"][0]["han"], "公回。")
        self.assertEqual(self.valid_count(), 0)

    def test_marks_are_saved_but_never_submitted(self) -> None:
        marked = {**self.row("001", "公回", "Ông về"), "danh_dau": "ocr", "ma": "a1", "ghi_chu": "mờ"}
        saved = self.save([marked, self.row("001", "改", "Đổi")], ["001"]).json()
        self.assertEqual(saved["rows"][0], marked)
        self.assertNotIn("danh_dau", saved["rows"][1])
        self.assertTrue(self.client.post(f"{self.URL}/nop").json()["nop"])
        self.assertEqual((self.book / "nom-1_parallel.tsv").read_text(encoding="utf-8"), "公回\tÔng về\n改\tĐổi\n")

    def test_bad_mark_is_rejected(self) -> None:
        for extra in ({"danh_dau": "khac"}, {"ma": "../x"}, {"ghi_chu": "x" * 501}):
            self.assertEqual(self.save([{**self.row("001", "公", "Ông"), **extra}], []).status_code, 422)

    def test_suggestions_come_from_their_own_file_and_are_not_saved_in_draft(self) -> None:
        self.assertEqual(self.client.get(self.URL).json()["goi_y"], {})
        (self.book / "goi_y.json").write_text(json.dumps({"a1": {"viet": "Gợi ý", "lan": 1}}), encoding="utf-8")
        self.assertEqual(self.client.get(self.URL).json()["goi_y"], {"a1": {"viet": "Gợi ý", "lan": 1}})
        marked = {**self.row("001", "公", ""), "danh_dau": "chua_dich", "ma": "a1"}
        self.save([marked], [])
        self.assertEqual(self.client.get(self.URL).json()["goi_y"], {"a1": {"viet": "Gợi ý", "lan": 1}})
        self.assertNotIn("goi_y", json.loads((self.book / "soat_nhap.json").read_text(encoding="utf-8")))

    def test_gutter_text_is_saved_but_never_submitted(self) -> None:
        self.assertEqual(self.client.get(self.URL).json()["ban_tam"], {})
        body = {"rows": [self.row("001", "公回", "Ông về")], "da_soat": ["001"], "phien_ban": 0, "ban_tam": {"001": "鄂氏宗譜 卷十"}}
        self.assertEqual(self.client.put(self.URL, json=body).status_code, 200)
        self.assertEqual(self.client.get(self.URL).json()["ban_tam"], {"001": "鄂氏宗譜 卷十"})
        self.assertTrue(self.client.post(f"{self.URL}/nop").json()["nop"])
        self.assertEqual(self.valid_count(), 1)
        self.assertEqual((self.book / "nom-1_parallel.tsv").read_text(encoding="utf-8"), "公回\tÔng về\n")

    def test_save_from_old_page_keeps_gutter_text(self) -> None:
        body = {"rows": [], "da_soat": [], "phien_ban": 0, "ban_tam": {"001": "鄂氏"}}
        self.client.put(self.URL, json=body)
        self.assertEqual(self.save([], [], phien_ban=1).json()["ban_tam"], {"001": "鄂氏"})

    def test_gutter_page_key_is_validated(self) -> None:
        body = {"rows": [], "da_soat": [], "phien_ban": 0, "ban_tam": {"../x": "鄂氏"}}
        self.assertEqual(self.client.put(self.URL, json=body).status_code, 422)

    def test_draft_saved_before_gutter_loads_with_empty_gutter(self) -> None:
        (self.book / "soat_nhap.json").write_text(json.dumps({"rows": [], "da_soat": [], "phien_ban": 2}), encoding="utf-8")
        body = self.client.get(self.URL).json()
        self.assertEqual((body["ban_tam"], body["phien_ban"]), ({}, 2))

    def test_stale_version_is_rejected(self) -> None:
        self.assertEqual(self.save([self.row("001", "公回。", "Ông về.")], []).status_code, 200)
        stale = self.save([self.row("001", "改。", "Đổi.")], [], phien_ban=0)
        self.assertEqual(stale.status_code, 409)
        self.assertEqual(self.client.get(self.URL).json()["rows"][0]["han"], "公回。")

    def test_submit_writes_only_confirmed_pages(self) -> None:
        rows = [
            self.row("001", "公回。", "Ông về."),
            self.row("001", "R.42", "số trang", bo=True),
            self.row("001", "", ""),
            self.row("002", "未審。", "Bản máy chưa soát."),
        ]
        self.save(rows, ["001"])
        body = self.client.post(f"{self.URL}/nop").json()
        self.assertEqual((body["nop"], body["so_cap"], body["tsv"]), (True, 1, "nom-1_parallel.tsv"))
        self.assertEqual((self.book / "nom-1_parallel.tsv").read_text(encoding="utf-8"), "公回。\tÔng về.\n")
        self.assertEqual(self.valid_count(), 1)

    def test_tab_and_newline_inside_cell_do_not_break_line(self) -> None:
        self.save([self.row("001", "公回\t改姓", "Ông về\nđổi họ")], ["001"])
        self.client.post(f"{self.URL}/nop")
        self.assertEqual((self.book / "nom-1_parallel.tsv").read_text(encoding="utf-8"), "公回 改姓\tÔng về đổi họ\n")

    def test_format_errors_block_submit(self) -> None:
        self.save([self.row("001", "公回。", "Ông về 字."), self.row("001", "改。", "")], ["001"])
        body = self.client.post(f"{self.URL}/nop").json()
        self.assertFalse(body["nop"])
        self.assertEqual([e["loi"] for e in body["loi"]], [["vế Việt lẫn chữ Hán"], ["thiếu một vế"]])
        self.assertFalse((self.book / "nom-1_parallel.tsv").exists())

    def test_nothing_confirmed_is_not_submitted(self) -> None:
        self.save([self.row("001", "公回。", "Ông về.")], [])
        body = self.client.post(f"{self.URL}/nop").json()
        self.assertEqual((body["nop"], body["so_cap"]), (False, 0))
        self.assertFalse((self.book / "nom-1_parallel.tsv").exists())

    def test_resubmit_keeps_previous_version(self) -> None:
        self.save([self.row("001", "公回。", "Ông về.")], ["001"])
        self.client.post(f"{self.URL}/nop")
        self.save([self.row("001", "公歸。", "Ông trở về.")], ["001"], phien_ban=1)
        self.client.post(f"{self.URL}/nop")
        self.assertEqual((self.book / "nom-1_parallel.tsv").read_text(encoding="utf-8"), "公歸。\tÔng trở về.\n")
        (old,) = (self.book / "lich_su").glob("*.tsv")
        self.assertEqual(old.read_text(encoding="utf-8"), "公回。\tÔng về.\n")
        self.assertEqual(self.client.get("/api/public/doi-chieu/sv-a/nom-1").json()["tsv"], "nom-1_parallel.tsv")

    def test_positions_require_admin_and_file(self) -> None:
        url = f"{self.URL}/khung/001"
        self.assertEqual(self.client.get(url).status_code, 404)
        (self.book / "khung").mkdir()
        payload = {"rong": 100, "cao": 200, "chu": [{"c": "公", "b": [1, 2, 3, 4]}], "thieu": 0}
        (self.book / "khung" / "001.json").write_text(json.dumps(payload), encoding="utf-8")
        self.assertEqual(self.client.get(url).json(), payload)
        self.assertEqual(self.client.get(f"{self.URL}/khung/..%2F..%2Fmeta").status_code, 404)
        self.login(UserRole.USER)
        self.assertEqual(self.client.get(url).status_code, 403)

    def machine_boxes(self) -> dict:
        (self.book / "khung").mkdir()
        payload = {
            "rong": 100,
            "cao": 200,
            "chu": [{"c": "公", "b": [1, 2, 3, 4], "u": 1}],
            "thieu": 2,
            "ban_tam": {"text": "鄂", "chu": [{"c": "鄂", "b": [5, 6, 7, 8]}], "thieu": 1},
        }
        (self.book / "khung" / "001.json").write_text(json.dumps(payload), encoding="utf-8")
        return payload

    def test_edited_boxes_replace_machine_boxes_but_keep_machine_file(self) -> None:
        machine = self.machine_boxes()
        url = f"{self.URL}/khung/001"
        body = {
            "chu": [{"c": "公", "b": [1, 2, 9, 9], "n": "sua"}, {"c": "回", "b": [10, 10, 20, 20], "n": "them"}],
            "ban_tam_chu": [],
            "phien_ban": 0,
        }
        saved = self.client.put(url, json=body).json()
        self.assertEqual(saved["chu"], body["chu"])
        self.assertEqual((saved["thieu"], saved["da_sua"], saved["phien_ban"]), (1, True, 1))
        self.assertEqual((saved["ban_tam"]["chu"], saved["ban_tam"]["text"]), ([], "鄂"))
        self.assertEqual(self.client.get(url).json(), saved)
        self.assertEqual(json.loads((self.book / "khung" / "001.json").read_text(encoding="utf-8")), machine)

    def test_restoring_boxes_returns_machine_and_keeps_edit_in_history(self) -> None:
        machine = self.machine_boxes()
        url = f"{self.URL}/khung/001"
        self.client.put(url, json={"chu": [], "phien_ban": 0})
        self.assertEqual(self.client.delete(url, params={"phien_ban": 0}).status_code, 409)
        self.assertEqual(self.client.delete(url, params={"phien_ban": 1}).json(), machine)
        self.assertEqual(self.client.get(url).json(), machine)
        (old,) = (self.book / "khung_sua" / "lich_su").glob("001_*.json")
        self.assertEqual(json.loads(old.read_text(encoding="utf-8"))["chu"], [])

    def test_stale_or_invalid_box_edit_is_rejected(self) -> None:
        self.machine_boxes()
        url = f"{self.URL}/khung/001"
        self.assertEqual(self.client.put(url, json={"chu": [], "phien_ban": 0}).status_code, 200)
        self.assertEqual(self.client.put(url, json={"chu": [], "phien_ban": 0}).status_code, 409)
        for cell in ({"c": "公", "b": [0, 0, 101, 5]}, {"c": "公", "b": [5, 0, 1, 5]}, {"c": "", "b": [0, 0, 1, 1]}, {"c": "公", "b": [0, 0, 1, 1], "n": "x"}):
            self.assertEqual(self.client.put(url, json={"chu": [cell], "phien_ban": 1}).status_code, 422)

    def test_box_edit_needs_machine_positions_and_admin(self) -> None:
        url = f"{self.URL}/khung/001"
        self.assertEqual(self.client.put(url, json={"chu": [], "phien_ban": 0}).status_code, 404)
        self.assertEqual(self.client.delete(url, params={"phien_ban": 0}).status_code, 404)
        self.assertEqual(self.client.put(f"{self.URL}/khung/..%2F..%2Fmeta", json={"chu": [], "phien_ban": 0}).status_code, 404)
        self.machine_boxes()
        self.login(UserRole.USER)
        self.assertEqual(self.client.put(url, json={"chu": [], "phien_ban": 0}).status_code, 403)
        self.assertEqual(self.client.delete(url, params={"phien_ban": 0}).status_code, 403)
        self.assertFalse((self.book / "khung_sua").exists())

    def test_box_edit_does_not_change_submission(self) -> None:
        self.machine_boxes()
        self.save([self.row("001", "公回。", "Ông về.")], ["001"])
        self.client.put(f"{self.URL}/khung/001", json={"chu": [], "phien_ban": 0})
        self.assertEqual(self.client.post(f"{self.URL}/nop").json()["so_cap"], 1)
        self.assertEqual((self.book / "nom-1_parallel.tsv").read_text(encoding="utf-8"), "公回。\tÔng về.\n")

    def test_existing_submission_is_not_overwritten_from_machine(self) -> None:
        tsv = self.book / "bai_cua_sinh_vien.tsv"
        tsv.write_text("公回。\tÔng về.\n", encoding="utf-8")
        self.assertEqual(self.client.get(self.URL).status_code, 409)
        self.assertEqual(self.save([self.row("001", "改。", "Đổi.")], ["001"]).status_code, 409)
        self.assertEqual(tsv.read_text(encoding="utf-8"), "公回。\tÔng về.\n")
