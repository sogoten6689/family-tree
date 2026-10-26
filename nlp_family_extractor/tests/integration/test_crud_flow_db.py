"""Luồng CRUD cây gia phả qua HTTP thật — cần API có MySQL + admin mặc định."""
from __future__ import annotations

import httpx
import pytest

pytestmark = pytest.mark.requires_db


def test_tree_node_link_export_flow(client: httpx.Client, admin_headers: dict[str, str]) -> None:
    created = client.post(
        "/api/family-trees",
        json={"name": "Harness tree", "description": "e2e"},
        headers=admin_headers,
    )
    assert created.status_code == 200, created.text
    tree_id = created.json()["id"]
    try:
        for name, gender in (("Ông A", "male"), ("Bà B", "female"), ("Con C", "male")):
            resp = client.post(
                f"/api/family-trees/{tree_id}/nodes",
                json={"name": name, "gender": gender},
                headers=admin_headers,
            )
            assert resp.status_code == 200, resp.text

        for link in (
            {"type": "spouse_of", "from_id": 1, "to_id": 2},
            {"type": "parent_of", "from_id": 1, "to_id": 3, "side": "fid"},  # parent_of bắt buộc side (fid/mid)
        ):
            resp = client.post(f"/api/family-trees/{tree_id}/links", json=link, headers=admin_headers)
            assert resp.status_code == 200, resp.text

        doc = client.get(f"/api/family-trees/{tree_id}", headers=admin_headers).json()
        nodes = {n["id"]: n for n in doc["nodes"]}
        assert len(nodes) == 3
        # liên kết nằm trong nút: vợ chồng = pids, cha/mẹ = fid/mid (không có mảng "links")
        assert nodes[1]["pids"] == [2] and nodes[3]["fid"] == 1

        listing = client.get("/api/family-trees", headers=admin_headers).json()
        assert any(item["id"] == tree_id for item in listing["items"])

        exported = client.get(
            f"/api/family-trees/{tree_id}/export", params={"format": "json"}, headers=admin_headers
        )
        assert exported.status_code == 200, exported.text
    finally:
        client.delete(f"/api/family-trees/{tree_id}", headers=admin_headers)

    assert client.get(f"/api/family-trees/{tree_id}", headers=admin_headers).status_code == 404


def test_anonymous_cannot_write(client: httpx.Client, admin_headers: dict[str, str]) -> None:
    resp = client.post("/api/family-trees", json={"name": "x"})
    assert resp.status_code in (401, 403)
