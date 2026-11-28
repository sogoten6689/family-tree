import unittest
from unittest import mock

from fastapi.testclient import TestClient

import api
from app.research_mode import is_blocked, research_mode

CLOSED = [
    ("POST", "/api/register"),
    ("PATCH", "/api/me"),
    ("PATCH", "/api/users/1/role"),
    ("DELETE", "/api/users/1"),
    ("POST", "/api/admin/settings"),
    ("POST", "/analyze"),
    ("POST", "/api/doi-chieu"),  # không có dấu / cuối → không thuộc phần soát
    ("POST", "/api/public/doi-chieu/x/y"),
]
OPEN = [
    ("POST", "/api/login"),
    ("PUT", "/api/doi-chieu/chua-giao/tq-696/soat"),
    ("PUT", "/api/doi-chieu/chua-giao/tq-696/soat/khung/004"),
    ("DELETE", "/api/doi-chieu/chua-giao/tq-696/soat/khung/004"),
    ("GET", "/api/admin/settings"),
    ("OPTIONS", "/api/register"),
]


class ResearchModeTest(unittest.TestCase):
    def test_flag_defaults_off(self) -> None:
        for value, expected in [("1", True), ("true", True), ("0", False), ("", False)]:
            with mock.patch.dict("os.environ", {"RESEARCH_MODE": value}):
                self.assertEqual(research_mode(), expected, value)

    def test_allow_list(self) -> None:
        for method, path in CLOSED:
            self.assertTrue(is_blocked(method, path), f"{method} {path}")
        for method, path in OPEN:
            self.assertFalse(is_blocked(method, path), f"{method} {path}")

    def test_every_write_route_is_closed_except_login_and_review(self) -> None:
        # Lấy route từ OpenAPI: bản FastAPI mới không còn trải route của router con vào app.routes.
        writes = [
            (method.upper(), path)
            for path, operations in api.app.openapi()["paths"].items()
            for method in operations
            if method.upper() in {"POST", "PUT", "PATCH", "DELETE"}
        ]
        opened = [(method, path) for method, path in writes if not is_blocked(method, path)]
        self.assertIn(("POST", "/api/login"), opened)
        self.assertGreater(len(writes), len(opened))
        for method, path in opened:
            self.assertTrue(path == "/api/login" or path.startswith("/api/doi-chieu/"), f"{method} {path}")

    def test_middleware_rejects_closed_write(self) -> None:
        client = TestClient(api.app)
        with mock.patch.dict("os.environ", {"RESEARCH_MODE": "1"}):
            response = client.post("/api/register", json={})
        self.assertEqual(response.status_code, 403)
        self.assertIn("chế độ nghiên cứu", response.json()["detail"])

    def test_middleware_inactive_when_off(self) -> None:
        client = TestClient(api.app)
        with mock.patch.dict("os.environ", {"RESEARCH_MODE": "0"}):
            response = client.post("/api/register", json={})
        self.assertNotEqual(response.status_code, 403)


if __name__ == "__main__":
    unittest.main()
