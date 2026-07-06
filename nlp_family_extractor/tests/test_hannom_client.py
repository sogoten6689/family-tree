import os
import unittest
from unittest.mock import patch

from app.hannom.client import (
    SUCCESS_CODE,
    _coerce_text_list,
    _extract_payload,
    get_auth_headers,
)
from app.hannom.errors import HannomApiError


class HannomClientTest(unittest.TestCase):
    def test_get_auth_headers_requires_token(self) -> None:
        with patch.dict(os.environ, {"HANNOM_API_TOKEN": ""}, clear=False):
            with self.assertRaises(HannomApiError):
                get_auth_headers()

    def test_get_auth_headers_with_token(self) -> None:
        with patch.dict(os.environ, {"HANNOM_API_TOKEN": "test-token"}, clear=False):
            headers = get_auth_headers()
        self.assertEqual(headers["Authorization"], "Bearer test-token")
        self.assertIn("Mozilla", headers["User-Agent"])
        self.assertNotIn("python-requests", headers["User-Agent"])

    def test_extract_payload_success(self) -> None:
        payload = _extract_payload({"code": SUCCESS_CODE, "data": {"file_name": "abc.jpg"}})
        self.assertEqual(payload["file_name"], "abc.jpg")

    def test_extract_payload_error_code(self) -> None:
        with self.assertRaises(HannomApiError) as ctx:
            _extract_payload({"code": "100001", "message": "Invalid token"})
        self.assertEqual(ctx.exception.api_code, "100001")

    def test_coerce_text_list(self) -> None:
        texts = _coerce_text_list(
            {"result_text_transcription": ["  dòng 1 ", "", "dòng 2"]},
            keys=("result_text_transcription",),
        )
        self.assertEqual(texts, ["dòng 1", "dòng 2"])


if __name__ == "__main__":
    unittest.main()
