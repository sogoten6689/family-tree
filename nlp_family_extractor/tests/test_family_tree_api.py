import tempfile
import unittest
from pathlib import Path

from fastapi.testclient import TestClient

import api
from app.family_tree_store import JsonFamilyTreeStore


class FamilyTreeApiCrudTest(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        api._family_tree_store = JsonFamilyTreeStore(Path(self.temp_dir.name))
        self.client = TestClient(api.app)

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    def test_tree_node_and_link_crud_flow(self) -> None:
        create_tree = self.client.post(
            "/api/family-trees",
            json={"name": "Gia phả test", "description": "crud"},
        )
        self.assertEqual(create_tree.status_code, 200)
        tree = create_tree.json()
        tree_id = tree["id"]

        list_trees = self.client.get("/api/family-trees")
        self.assertEqual(list_trees.status_code, 200)
        self.assertEqual(list_trees.json()["total"], 1)

        update_tree = self.client.put(
            f"/api/family-trees/{tree_id}",
            json={"name": "Gia phả test updated"},
        )
        self.assertEqual(update_tree.status_code, 200)
        self.assertEqual(update_tree.json()["name"], "Gia phả test updated")

        add_node_1 = self.client.post(
            f"/api/family-trees/{tree_id}/nodes",
            json={"name": "Ông A", "gender": "male"},
        )
        self.assertEqual(add_node_1.status_code, 200)

        add_node_2 = self.client.post(
            f"/api/family-trees/{tree_id}/nodes",
            json={"name": "Bà B", "gender": "female"},
        )
        self.assertEqual(add_node_2.status_code, 200)

        add_node_3 = self.client.post(
            f"/api/family-trees/{tree_id}/nodes",
            json={"name": "Con C", "gender": "male"},
        )
        self.assertEqual(add_node_3.status_code, 200)

        create_spouse_link = self.client.post(
            f"/api/family-trees/{tree_id}/links",
            json={"type": "spouse_of", "from_id": 1, "to_id": 2},
        )
        self.assertEqual(create_spouse_link.status_code, 200)

        create_parent_link = self.client.post(
            f"/api/family-trees/{tree_id}/links",
            json={"type": "parent_of", "from_id": 1, "to_id": 3, "side": "fid"},
        )
        self.assertEqual(create_parent_link.status_code, 200)

        update_node = self.client.put(
            f"/api/family-trees/{tree_id}/nodes/3",
            json={"birthYear": 1990},
        )
        self.assertEqual(update_node.status_code, 200)

        tree_detail = self.client.get(f"/api/family-trees/{tree_id}")
        self.assertEqual(tree_detail.status_code, 200)
        nodes = tree_detail.json()["nodes"]
        child = next(node for node in nodes if node["id"] == 3)
        self.assertEqual(child["fid"], 1)
        self.assertEqual(child["birthYear"], 1990)

        replace_doc = self.client.put(
            f"/api/family-trees/{tree_id}/document",
            json={
                "name": "Gia phả sửa từ JSON",
                "description": "edited",
                "nodes": [
                    {"id": 1, "name": "Ông A", "gender": "male"},
                    {"id": 2, "name": "Bà B", "gender": "female", "pids": [1]},
                ],
            },
        )
        self.assertEqual(replace_doc.status_code, 200)
        self.assertEqual(replace_doc.json()["name"], "Gia phả sửa từ JSON")
        self.assertEqual(len(replace_doc.json()["nodes"]), 2)

        delete_spouse_link = self.client.request(
            "DELETE",
            f"/api/family-trees/{tree_id}/links",
            json={"type": "spouse_of", "from_id": 1, "to_id": 2},
        )
        self.assertEqual(delete_spouse_link.status_code, 200)

        delete_tree = self.client.delete(f"/api/family-trees/{tree_id}")
        self.assertEqual(delete_tree.status_code, 200)


if __name__ == "__main__":
    unittest.main()
