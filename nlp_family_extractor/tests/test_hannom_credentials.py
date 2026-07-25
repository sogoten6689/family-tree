import os
import unittest
from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock, patch

from app.hannom.credential_store import HannomCredentialStore, _encrypt, _decrypt
from app.hannom.jwt_utils import is_token_expiring_soon, parse_jwt_expiry
from app.hannom.models import HannomCredential, SINGLETON_ID


def _make_jwt(*, exp: int) -> str:
    import base64
    import json

    header = base64.urlsafe_b64encode(json.dumps({"alg": "HS256", "typ": "JWT"}).encode()).decode().rstrip("=")
    payload = base64.urlsafe_b64encode(json.dumps({"exp": exp}).encode()).decode().rstrip("=")
    return f"{header}.{payload}.signature"


class HannomJwtUtilsTest(unittest.TestCase):
    def test_parse_jwt_expiry(self) -> None:
        exp_ts = int((datetime.now(timezone.utc) + timedelta(hours=1)).timestamp())
        token = _make_jwt(exp=exp_ts)
        parsed = parse_jwt_expiry(token)
        self.assertIsNotNone(parsed)
        assert parsed is not None
        self.assertAlmostEqual(parsed.timestamp(), float(exp_ts), delta=1)

    def test_is_token_expiring_soon(self) -> None:
        soon = int((datetime.now(timezone.utc) + timedelta(minutes=1)).timestamp())
        later = int((datetime.now(timezone.utc) + timedelta(hours=2)).timestamp())
        self.assertTrue(is_token_expiring_soon(_make_jwt(exp=soon)))
        self.assertFalse(is_token_expiring_soon(_make_jwt(exp=later)))


class HannomCredentialStoreTest(unittest.TestCase):
    def setUp(self) -> None:
        os.environ.setdefault("JWT_SECRET_KEY", "test-secret-for-hannom-credentials")

    def test_encrypt_roundtrip(self) -> None:
        self.assertEqual(_decrypt(_encrypt("secret-value")), "secret-value")

    @patch("app.hannom.credential_store.fetch_hannom_token")
    def test_save_and_login_persists_row(self, fetch_mock: MagicMock) -> None:
        fetch_mock.return_value = {
            "token": _make_jwt(exp=int((datetime.now(timezone.utc) + timedelta(hours=1)).timestamp())),
            "source": "cookie:token",
        }
        db = MagicMock()
        db.get.return_value = None
        store = HannomCredentialStore()

        store.save_and_login(db, username="user@test.com", password="pass123")

        self.assertTrue(db.add.called)
        added = db.add.call_args[0][0]
        self.assertIsInstance(added, HannomCredential)
        self.assertEqual(added.id, SINGLETON_ID)
        self.assertEqual(added.username, "user@test.com")

    @patch("app.hannom.credential_store.fetch_hannom_token")
    def test_get_valid_token_uses_cached_when_not_expiring(self, fetch_mock: MagicMock) -> None:
        token = _make_jwt(exp=int((datetime.now(timezone.utc) + timedelta(hours=2)).timestamp()))
        row = HannomCredential(
            id=SINGLETON_ID,
            username="user@test.com",
            password_enc=_encrypt("pass123"),
            token_enc=_encrypt(token),
        )
        db = MagicMock()
        db.get.return_value = row
        store = HannomCredentialStore()

        result = store._get_valid_token_with_session(db)

        self.assertEqual(result, token)
        fetch_mock.assert_not_called()


if __name__ == "__main__":
    unittest.main()
