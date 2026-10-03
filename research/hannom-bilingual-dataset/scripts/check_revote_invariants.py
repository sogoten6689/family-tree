"""Kiểm tra bất biến của revote_paddle_order.py trên BẢN SAO dữ liệu (không đụng data thật).

Copy `DATA_REPO_ROOT/data` sang thư mục tạm, chạy `revote_paddle_order.py --write`
2 lần với HANNOM_DATA_ROOT trỏ vào bản sao, rồi kiểm tra:

  B1  Paddle đọc lại (JSON, sắp theo cột) có ĐÚNG tập dòng như bản đã lưu.
  B2  Text của mọi engine khác paddle_v6 không đổi.
  B3  Engine nền (backbone) của vote không đổi.
  B4  voted_text chỉ đổi thứ tự (tập dòng giữ nguyên) — liệt kê trang ngoại lệ.
  B5  Chạy --write lần 2 không đổi gì (idempotent).
  E2  Ngoài 6 trường L1 của vote, không trường nào của record/trang bị đổi;
      record không có trang đổi thì giữ nguyên từng byte.
  E3  Mọi record vẫn hợp lệ theo schema/bilingual_record.schema.json.

Chạy: python3 scripts/check_revote_invariants.py   (exit 1 nếu có bất biến hỏng)
"""

from __future__ import annotations

import glob
import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
from collections import Counter
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPTS))
from _repo_paths import DATA_REPO_ROOT  # noqa: E402
from revote_paddle_order import L1_VOTE_FIELDS, nonempty_lines  # noqa: E402

SCHEMA = SCRIPTS.parent / "schema" / "bilingual_record.schema.json"


def digest(value) -> str:
    return hashlib.sha256(json.dumps(value, ensure_ascii=False, sort_keys=True).encode()).hexdigest()


def snapshot(root: Path) -> dict[str, dict]:
    out = {}
    for path in sorted(glob.glob(str(root / "data" / "track*" / "*.json"))):
        raw = Path(path).read_bytes()
        out[Path(path).relative_to(root).as_posix()] = {"bytes": raw, "record": json.loads(raw)}
    return out


def run_write(root: Path) -> str:
    env = {**os.environ, "HANNOM_DATA_ROOT": str(root)}
    proc = subprocess.run(
        [sys.executable, str(SCRIPTS / "revote_paddle_order.py"), "--write"],
        env=env, capture_output=True, text=True, check=True,
    )
    return proc.stdout


def main() -> int:
    failures: list[str] = []

    def check(ok: bool, label: str, detail: str = "") -> None:
        print(f"  [{'OK ' if ok else 'FAIL'}] {label}" + (f" — {detail}" if detail else ""))
        if not ok:
            failures.append(label)

    with tempfile.TemporaryDirectory(prefix="revote-check-") as tmp:
        copy = Path(tmp)
        shutil.copytree(DATA_REPO_ROOT / "data", copy / "data")
        before = snapshot(copy)
        print("Lần ghi 1:\n" + run_write(copy))
        after = snapshot(copy)
        print("Lần ghi 2:\n" + run_write(copy))
        again = snapshot(copy)

        pages_changed = reorder_only = 0
        content_changed: list[str] = []
        engine_drift: list[str] = []
        backbone_drift: list[str] = []
        paddle_line_drift: list[str] = []
        other_field_drift: list[str] = []
        untouched_bytes_drift: list[str] = []

        for name, old in before.items():
            new = after[name]
            old_rec, new_rec = old["record"], new["record"]
            if {k: v for k, v in old_rec.items() if k != "pages"} != {k: v for k, v in new_rec.items() if k != "pages"}:
                other_field_drift.append(f"{name}: trường cấp record")
            record_changed = False
            for i, (op, np_) in enumerate(zip(old_rec.get("pages", []), new_rec.get("pages", []))):
                where = f"{old_rec['doc_id']}/{op.get('page_id')}"
                if {k: v for k, v in op.items() if k != "l1_ocr"} != {k: v for k, v in np_.items() if k != "l1_ocr"}:
                    other_field_drift.append(where)
                ol1, nl1 = op.get("l1_ocr") or {}, np_.get("l1_ocr") or {}
                extra = set(ol1) | set(nl1)
                if {k: ol1.get(k) for k in extra - set(L1_VOTE_FIELDS)} != {k: nl1.get(k) for k in extra - set(L1_VOTE_FIELDS)}:
                    other_field_drift.append(f"{where}: trường L1 ngoài vote")
                if digest(ol1) == digest(nl1):
                    continue
                record_changed = True
                pages_changed += 1
                oe, ne = ol1.get("engines") or {}, nl1.get("engines") or {}
                if set(oe) != set(ne) or any(oe[k].get("text") != ne[k].get("text") for k in oe if k != "paddle_v6"):
                    engine_drift.append(where)
                if Counter(nonempty_lines(oe["paddle_v6"].get("text"))) != Counter(nonempty_lines(ne["paddle_v6"].get("text"))):
                    paddle_line_drift.append(where)
                if (ol1.get("vote_method") or "").split("_backbone")[0] != (nl1.get("vote_method") or "").split("_backbone")[0]:
                    backbone_drift.append(where)
                if Counter(nonempty_lines(ol1.get("voted_text"))) == Counter(nonempty_lines(nl1.get("voted_text"))):
                    reorder_only += 1
                else:
                    content_changed.append(where)
            if not record_changed and old["bytes"] != new["bytes"]:
                untouched_bytes_drift.append(name)

        print("Bất biến:")
        check(not paddle_line_drift, "B1 Paddle giữ đúng tập dòng", f"{len(paddle_line_drift)} trang lệch")
        check(not engine_drift, "B2 Engine khác không đổi", f"{len(engine_drift)} trang lệch")
        check(not backbone_drift, "B3 Backbone không đổi", f"{len(backbone_drift)} trang lệch")
        print(f"  [info] {pages_changed} trang đổi L1: {reorder_only} chỉ đổi thứ tự, {len(content_changed)} đổi nội dung")
        print(f"         đổi nội dung: {', '.join(content_changed)}")
        check(all(after[n]["bytes"] == again[n]["bytes"] for n in after), "B5 Ghi lần 2 không đổi gì (idempotent)")
        check(not other_field_drift, "E2 Ngoài 6 trường vote L1 không gì đổi", "; ".join(other_field_drift[:5]))
        check(not untouched_bytes_drift, "E2 Record không có trang đổi giữ nguyên từng byte", ", ".join(untouched_bytes_drift[:5]))

        try:
            import jsonschema
        except ImportError:
            check(False, "E3 Schema", "thiếu gói jsonschema")
        else:
            validator = jsonschema.Draft7Validator(json.loads(SCHEMA.read_text(encoding="utf-8")))
            errors_before = sum(len(list(validator.iter_errors(v["record"]))) for v in before.values())
            errors_after = sum(len(list(validator.iter_errors(v["record"]))) for v in after.values())
            check(errors_after <= errors_before, "E3 Schema không thêm lỗi", f"lỗi trước={errors_before}, sau={errors_after}")

    print("\nKẾT QUẢ: " + ("ĐẠT" if not failures else "HỎNG: " + ", ".join(failures)))
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
