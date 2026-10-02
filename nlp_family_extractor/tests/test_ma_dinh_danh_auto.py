import json
import unittest
from unittest import mock

from fastapi.testclient import TestClient

import api
from app.auth.dependencies import get_current_user
from app.database import get_db
from app.workspace.ma_dinh_danh import next_sequence_for_letter
from app.workspace.ma_dinh_danh_auto import ensure_ma_dinh_danh, parse_response
from app.workspace.router import require_workspace_database
from tests.test_corpus_identifiers import _Db

GOOD = {"quy_mo": "Tộc phả", "hinh_thuc": "Bộ", "ho": "Nguyễn", "dia_danh_ngan": "Bối Khê", "nam_soan_goc": 1496}


def fake_gemini(payload):
    calls = []

    def generate(prompt):
        calls.append(prompt)
        return "Kết quả:\n```json\n" + json.dumps(payload, ensure_ascii=False) + "\n```"

    generate.calls = calls
    return generate


class ParseResponseTest(unittest.TestCase):
    def test_valid(self) -> None:
        inputs, problems = parse_response(json.dumps(GOOD, ensure_ascii=False))
        self.assertEqual(problems, [])
        self.assertEqual(inputs["ho_toc"], "Nguyễn")

    def test_year_as_numeric_string_ok(self) -> None:
        inputs, _ = parse_response(json.dumps({**GOOD, "nam_soan_goc": "1496"}, ensure_ascii=False))
        self.assertEqual(inputs["nam_soan_goc"], 1496)

    def test_any_invalid_field_blocks_code(self) -> None:
        for bad in ({"quy_mo": "Đại phả"}, {"hinh_thuc": None}, {"ho": ""}, {"dia_danh_ngan": "123"}, {"nam_soan_goc": 3000}):
            inputs, problems = parse_response(json.dumps({**GOOD, **bad}, ensure_ascii=False))
            self.assertIsNone(inputs, bad)
            self.assertTrue(problems)

    def test_not_json(self) -> None:
        self.assertEqual(parse_response("không biết")[0], None)


class SequenceTest(unittest.TestCase):
    CODES = ["F-B-PN-GiaThien-001-1930", "F-B-NG-BoiKhe-008-1496", "F-M-NG-TayTuu-009-1844", "rác"]

    def test_per_letter(self) -> None:
        self.assertEqual(next_sequence_for_letter(self.CODES, "B"), 9)
        self.assertEqual(next_sequence_for_letter(self.CODES, "M"), 10)
        self.assertEqual(next_sequence_for_letter(self.CODES, "K"), 1)

    def test_overflow(self) -> None:
        with self.assertRaises(ValueError):
            next_sequence_for_letter(["F-B-NG-X-999-1900"], "B")


class EnsureTest(_Db, unittest.TestCase):
    def test_creates_code_after_existing_max_in_same_letter(self) -> None:
        old = self.new_scan()
        self.scans.set_corpus_identifiers(old, {"ma_dinh_danh": "F-B-PN-GiaThien-001-1930", "ma_dinh_danh_nguon": "catalogue"})
        other_letter = self.new_scan()
        self.scans.set_corpus_identifiers(other_letter, {"ma_dinh_danh": "F-M-NG-TayTuu-009-1844"})
        scan = self.new_scan(source_text="bản dịch…")
        scan, problems = ensure_ma_dinh_danh(self.scans, scan, fake_gemini(GOOD))
        self.assertEqual(problems, [])
        self.assertEqual(scan.ma_dinh_danh, "F-B-NG-BoiKhe-002-1496")  # chữ B: sau 001; không tính 009 của chữ M
        self.assertEqual(scan.ma_dinh_danh_nguon, "gemini")
        self.assertEqual(scan.quy_mo, "Tộc phả")

    def test_existing_code_kept_and_gemini_not_called(self) -> None:
        scan = self.new_scan(source_text="x")
        self.scans.set_corpus_identifiers(scan, {"ma_dinh_danh": "F-B-PN-GiaThien-001-1930", "ma_dinh_danh_nguon": "catalogue"})
        generate = fake_gemini(GOOD)
        scan, _ = ensure_ma_dinh_danh(self.scans, scan, generate)
        self.assertEqual(scan.ma_dinh_danh, "F-B-PN-GiaThien-001-1930")
        self.assertEqual(generate.calls, [])

    def test_no_text_does_not_call_gemini(self) -> None:
        generate = fake_gemini(GOOD)
        scan, problems = ensure_ma_dinh_danh(self.scans, self.new_scan(), generate)
        self.assertIsNone(scan.ma_dinh_danh)
        self.assertEqual(generate.calls, [])
        self.assertTrue(problems)

    def test_gemini_error_and_missing_key_reported_not_raised(self) -> None:
        def boom(prompt):
            raise ValueError("GOOGLE_API_KEY is not set")

        scan, problems = ensure_ma_dinh_danh(self.scans, self.new_scan(source_text="x"), boom)
        self.assertIsNone(scan.ma_dinh_danh)
        self.assertIn("GOOGLE_API_KEY", problems[0])
        with mock.patch("app.workspace.ma_dinh_danh_auto.default_generate", side_effect=ValueError("no key")):
            scan, problems = ensure_ma_dinh_danh(self.scans, self.new_scan(source_text="x"))
        self.assertIn("no key", problems[0])

    def test_invalid_answer_leaves_scan_without_code(self) -> None:
        scan, problems = ensure_ma_dinh_danh(self.scans, self.new_scan(source_text="x"), fake_gemini({**GOOD, "ho": None}))
        self.assertIsNone(scan.ma_dinh_danh)
        self.assertTrue(problems)


class AutoEndpointTest(_Db, unittest.TestCase):
    def setUp(self) -> None:
        super().setUp()
        self.scan = self.new_scan(source_text="bản dịch")
        api.app.dependency_overrides[get_db] = lambda: self.db
        api.app.dependency_overrides[get_current_user] = lambda: self.owner
        api.app.dependency_overrides[require_workspace_database] = lambda: None
        self.client = TestClient(api.app)

    def tearDown(self) -> None:
        api.app.dependency_overrides.clear()
        super().tearDown()

    def test_endpoint_creates_code(self) -> None:
        with mock.patch("app.workspace.ma_dinh_danh_auto.default_generate", return_value=fake_gemini(GOOD)):
            body = self.client.post(f"/api/user/documents/{self.scan.id}/ma-dinh-danh/auto").json()
        self.assertEqual((body["ma_dinh_danh"], body["ma_dinh_danh_nguon"]), ("F-B-NG-BoiKhe-001-1496", "gemini"))

    def test_scan_detail_exposes_code(self) -> None:
        self.scans.set_corpus_identifiers(self.scan, {"ma_dinh_danh": "F-B-PN-GiaThien-001-1930", "ma_dinh_danh_nguon": "catalogue"})
        body = self.client.get(f"/api/user/documents/{self.scan.id}").json()
        self.assertEqual((body["ma_dinh_danh"], body["ma_dinh_danh_nguon"]), ("F-B-PN-GiaThien-001-1930", "catalogue"))


if __name__ == "__main__":
    unittest.main()
