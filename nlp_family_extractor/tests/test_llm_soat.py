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
from app.doi_chieu import llm_soat
from app.research_mode import is_blocked

INSTR = "Trích xuất thực thể và quan hệ gia phả từ văn bản sau. Trả về dạng JSON."


def record(inp: str, persons: list[dict], relations: list[dict], meta: dict | None = None) -> str:
    ans = json.dumps({"persons": persons, "relations": relations}, ensure_ascii=False)
    rec = {"text": f"### Instruction:\n{INSTR}\n\n### Input:\n{inp}\n\n### Response:\n{ans}"}
    if meta:
        rec["meta"] = meta
    return json.dumps(rec, ensure_ascii=False)


P = lambda n, g="male", gen=1: {"name": n, "birth": None, "death": None, "generation": gen, "gender": g}


class LlmSoatTest(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.dir = Path(self.tmp.name)
        lines = [
            record("Ông Lê Văn An lấy bà Trần Thị Bình.", [P("Lê Văn An"), P("Trần Thị Bình", "female")],
                   [{"from": "Lê Văn An", "to": "Trần Thị Bình", "type": "spouse"}]),
            record("Đoạn kể chuyện, không có ai.", [], [], {"tree_id": 1}),
        ]
        (self.dir / "a.jsonl").write_text("\n".join(lines) + "\n", encoding="utf-8")
        (self.dir / "chat.jsonl").write_text('{"messages": []}\n', encoding="utf-8")  # không phải dạng Alpaca -> bỏ qua
        self.old = os.environ.get("LLM_SOAT_DIRS")
        os.environ["LLM_SOAT_DIRS"] = str(self.dir)
        api.app.dependency_overrides[get_db] = lambda: None
        self.client = TestClient(api.app)
        self.login(UserRole.ADMIN)

    def tearDown(self) -> None:
        api.app.dependency_overrides.clear()
        if self.old is None:
            os.environ.pop("LLM_SOAT_DIRS", None)
        else:
            os.environ["LLM_SOAT_DIRS"] = self.old
        self.tmp.cleanup()

    def login(self, role: UserRole) -> None:
        user = SimpleNamespace(role=role, email="nguoi-soat@example.test")
        api.app.dependency_overrides[get_current_user] = lambda: user

    def ds(self) -> dict:
        body = self.client.get("/api/doi-chieu/llm").json()
        self.assertEqual(len(body["datasets"]), 1)
        return body["datasets"][0]

    def test_list_and_detail(self) -> None:
        d = self.ds()
        self.assertEqual((d["label"], d["mau"], d["co_quan_he"]), ("a.jsonl", 2, 1))
        detail = self.client.get(f"/api/doi-chieu/llm/{d['id']}").json()
        s0 = detail["samples"][0]
        self.assertEqual(s0["input"], "Ông Lê Văn An lấy bà Trần Thị Bình.")
        self.assertEqual(len(s0["answer"]["persons"]), 2)
        self.assertIsNone(s0["review"])
        self.assertEqual(detail["samples"][1]["meta"], {"tree_id": 1})

    def test_review_saved_beside_file_and_exported(self) -> None:
        d = self.ds()
        s0 = self.client.get(f"/api/doi-chieu/llm/{d['id']}").json()["samples"][0]
        v0 = self.client.get("/api/doi-chieu/llm/phien-ban").json()["version"]
        fixed = {"persons": [P("Lê Văn An"), P("Trần Thị Bình", "female")],
                 "relations": [{"from": "Lê Văn An", "to": "Trần Thị Bình", "type": "spouse"}]}
        fixed["persons"][1]["birth"] = 1900
        r = self.client.put(f"/api/doi-chieu/llm/{d['id']}/soat/{s0['key']}", json={"status": "da", "note": "ok", "answer": fixed})
        self.assertEqual(r.status_code, 200, r.text)
        saved = json.loads((self.dir / "a.reviews.json").read_text(encoding="utf-8"))["items"][s0["key"]]
        self.assertEqual((saved["status"], saved["answer"]["persons"][1]["birth"]), ("da", 1900))
        self.assertEqual(saved["answer"]["relations"][0]["from"], "Lê Văn An")  # giữ khoá "from"
        self.assertNotEqual(self.client.get("/api/doi-chieu/llm/phien-ban").json()["version"], v0)
        self.assertEqual(self.ds()["da_soat"], 1)
        # file gốc không đổi; xuất ra .reviewed.jsonl
        self.assertNotIn("1900", (self.dir / "a.jsonl").read_text(encoding="utf-8"))
        out = self.client.post(f"/api/doi-chieu/llm/{d['id']}/xuat").json()
        self.assertEqual((out["count"], out["edited"]), (2, 1))
        first = json.loads((self.dir / "a.reviewed.jsonl").read_text(encoding="utf-8").split("\n")[0])
        self.assertIn('"birth": 1900', first["text"])
        self.assertEqual(first["meta"]["review_status"], "da")
        # file đã xuất không hiện thành bộ mới
        self.assertEqual(len(self.client.get("/api/doi-chieu/llm").json()["datasets"]), 1)
        # bỏ soát
        self.assertEqual(self.client.delete(f"/api/doi-chieu/llm/{d['id']}/soat/{s0['key']}").status_code, 200)
        self.assertEqual(self.ds()["da_soat"], 0)

    def test_new_file_appears(self) -> None:
        (self.dir / "sub").mkdir()
        (self.dir / "sub" / "b.jsonl").write_text(record("Ông Hồ Văn Cự.", [P("Hồ Văn Cự")], []) + "\n", encoding="utf-8")
        labels = sorted(d["label"] for d in self.client.get("/api/doi-chieu/llm").json()["datasets"])
        self.assertEqual(labels, ["a.jsonl", "sub/b.jsonl"])

    def test_rejects_bad_input(self) -> None:
        d = self.ds()
        base = f"/api/doi-chieu/llm/{d['id']}/soat"
        self.assertEqual(self.client.put(f"{base}/{'0' * 16}", json={"status": "da"}).status_code, 404)
        self.assertGreaterEqual(self.client.put(f"{base}/../../x", json={"status": "da"}).status_code, 400)
        self.assertEqual(self.client.get("/api/doi-chieu/llm/khongphaiid").status_code, 422)
        key = self.client.get(f"/api/doi-chieu/llm/{d['id']}").json()["samples"][0]["key"]
        bad = {"status": "da", "answer": {"persons": [], "relations": [{"from": "A", "to": "B", "type": "uncle"}]}}
        self.assertEqual(self.client.put(f"{base}/{key}", json=bad).status_code, 422)

    def test_requires_admin(self) -> None:
        api.app.dependency_overrides.pop(get_current_user)
        self.assertEqual(self.client.get("/api/doi-chieu/llm").status_code, 401)
        self.login(UserRole.USER)
        self.assertEqual(self.client.get("/api/doi-chieu/llm").status_code, 403)

    def test_writes_allowed_in_research_mode(self) -> None:
        self.assertFalse(is_blocked("PUT", "/api/doi-chieu/llm/0123456789/soat/0123456789abcdef"))
        self.assertFalse(is_blocked("POST", "/api/doi-chieu/llm/0123456789/xuat"))

    def test_routes_not_shadowed_by_book_routes(self) -> None:
        # /api/doi-chieu/{student}/{book}/soat không được nuốt route của LLM
        d = self.ds()
        r = self.client.get(f"/api/doi-chieu/llm/{d['id']}")
        self.assertIn("samples", r.json())

    def test_no_data_dir(self) -> None:
        os.environ["LLM_SOAT_DIRS"] = str(self.dir / "khong-co")
        self.assertEqual(self.client.get("/api/doi-chieu/llm").json()["datasets"], [])
        self.assertIsNone(llm_soat.pha_he_lines(1, ["x"]) if llm_soat.data_repo() is None else None)


if __name__ == "__main__":
    unittest.main()
