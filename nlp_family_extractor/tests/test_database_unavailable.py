import unittest
from unittest import mock

from fastapi.testclient import TestClient

import api
from app import database


class DatabaseUnavailableTest(unittest.TestCase):
    """Không có MySQL: route cần DB trả 503 (trước đây 500 vì get_db() ném RuntimeError)."""

    def setUp(self) -> None:
        patcher = mock.patch.object(database, "_SessionLocal", None)
        patcher.start()
        self.addCleanup(patcher.stop)
        self.client = TestClient(api.app)

    def test_admin_route_returns_503(self) -> None:
        resp = self.client.get("/api/family-trees", headers={"Authorization": "Bearer x"})
        self.assertEqual(resp.status_code, 503)
        self.assertIn("Database", resp.json()["detail"])

    def test_anonymous_admin_route_returns_503(self) -> None:
        self.assertEqual(self.client.get("/api/family-trees").status_code, 503)

    def test_still_a_runtime_error_for_direct_callers(self) -> None:
        with self.assertRaises(RuntimeError):
            next(database.get_db())


if __name__ == "__main__":
    unittest.main()
