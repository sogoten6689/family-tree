import unittest

from app.hannom.auth import _extract_token_from_json, _mask_token, _normalize_bearer_token


class HannomAuthTest(unittest.TestCase):
    def test_extract_token_from_nested_data(self) -> None:
        payload = {
            "code": "000000",
            "data": {"access_token": "eyJhbGci.test.signature"},
        }
        token = _extract_token_from_json(payload)
        self.assertEqual(token, "eyJhbGci.test.signature")

    def test_normalize_bearer_prefix(self) -> None:
        self.assertEqual(_normalize_bearer_token("Bearer abc.def.ghi"), "abc.def.ghi")

    def test_mask_token(self) -> None:
        masked = _mask_token("eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.payload.sig")
        self.assertTrue(masked.startswith("eyJhbGci"))
        self.assertTrue(masked.endswith("sig"))


if __name__ == "__main__":
    unittest.main()
