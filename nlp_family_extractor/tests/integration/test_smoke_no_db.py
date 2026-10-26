"""Smoke test API thật, không cần MySQL."""
from __future__ import annotations

import httpx

EXPECTED_ROUTES = [
    "/health",
    "/api/login",
    "/api/register",
    "/api/family-trees",
    "/api/family-trees/{tree_id}/nodes",
    "/api/family-trees/{tree_id}/links",
    "/api/family-trees/{tree_id}/export",
    "/api/public/family-trees/{tree_id}/export",
    "/api/genealogy/extract",
]


def test_health(client: httpx.Client) -> None:
    resp = client.get("/health")
    assert resp.status_code == 200
    assert isinstance(resp.json(), dict)


def test_openapi_lists_core_routes(client: httpx.Client) -> None:
    paths = client.get("/openapi.json").json()["paths"]
    missing = [route for route in EXPECTED_ROUTES if route not in paths]
    assert not missing, f"thiếu route: {missing}"


def test_docs_page(client: httpx.Client) -> None:
    assert client.get("/docs").status_code == 200


def test_login_without_db_is_503(client: httpx.Client, db_enabled: bool) -> None:
    if db_enabled:
        return
    resp = client.post("/api/login", json={"email": "a@b.co", "password": "x"})
    assert resp.status_code == 503


def test_admin_routes_reject_anonymous(client: httpx.Client) -> None:
    resp = client.get("/api/family-trees")
    # Có DB: 401. Không DB: 503 (DatabaseUnavailable, sửa 25/10/2026; trước đó là 500).
    assert resp.status_code in (401, 403, 503)
    assert "items" not in resp.text


def test_genealogy_extract_rejects_empty_text(client: httpx.Client) -> None:
    resp = client.post("/api/genealogy/extract", json={"text": "   "})
    assert resp.status_code == 400


def test_genealogy_extract_hannom_is_honest_failure(client: httpx.Client) -> None:
    resp = client.post("/api/genealogy/extract", json={"text": "阮文甲", "language": "hannom"})
    assert resp.status_code == 200
    body = resp.json()
    assert body["success"] is False
    assert body["error"]


def test_cors_preflight(client: httpx.Client) -> None:
    resp = client.options(
        "/health",
        headers={"Origin": "http://localhost:8080", "Access-Control-Request-Method": "GET"},
    )
    assert resp.status_code == 200
    assert "access-control-allow-origin" in resp.headers
