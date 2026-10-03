"""Kiểm tra bất biến của revote_char_records.py --write trên BẢN SAO dữ liệu.

Copy `DATA_REPO_ROOT/data` sang thư mục tạm, chạy --write 2 lần, kiểm tra:
  1. Chỉ `l1_ocr` đổi, và chỉ ở trang có engine; mọi trường khác (l2, l3, pairs,
     ghi chú, trường cấp record) giữ nguyên; record không đổi giữ nguyên từng byte.
  2. l1_ocr mới đủ trường schema 2; voted_text chỉ gồm chữ Hán + xuống dòng.
  3. Text từng engine (trừ paddle_v6 — đọc lại theo cột) không đổi; paddle giữ đúng tập dòng.
  4. Ghi lần 2 không đổi gì (idempotent).
  5. Schema (bản trong family-tree) không thêm lỗi.

Chạy: python3 scripts/check_char_revote.py   (exit 1 nếu hỏng)
"""

from __future__ import annotations

import glob
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
from vote_char_majority import han_only  # noqa: E402

SCHEMA = SCRIPTS.parent / "schema" / "bilingual_record.schema.json"
REQUIRED = {"voted_text", "schema_version", "vote_method", "backbone", "page_status", "thresholds", "stats",
            "review_rate", "uncertain_rate", "engines", "slots", "downstream_stale"}


def snapshot(root: Path) -> dict[str, dict]:
    return {
        Path(p).relative_to(root).as_posix(): {"bytes": Path(p).read_bytes(), "record": json.loads(Path(p).read_bytes())}
        for p in sorted(glob.glob(str(root / "data" / "track*" / "*.json")))
    }


def lines_of(text: str | None) -> Counter:
    return Counter(line.strip() for line in (text or "").splitlines() if line.strip())


def main() -> int:
    failures: list[str] = []

    def check(ok: bool, label: str, detail: str = "") -> None:
        print(f"  [{'OK ' if ok else 'FAIL'}] {label}" + (f" — {detail}" if detail else ""))
        if not ok:
            failures.append(label)

    with tempfile.TemporaryDirectory(prefix="char-revote-") as tmp:
        copy = Path(tmp)
        shutil.copytree(DATA_REPO_ROOT / "data", copy / "data")
        env = {**os.environ, "HANNOM_DATA_ROOT": str(copy)}
        run = lambda: subprocess.run(  # noqa: E731
            [sys.executable, str(SCRIPTS / "revote_char_records.py"), "--write"], env=env, check=True, capture_output=True, text=True
        ).stdout
        before = snapshot(copy)
        out1 = run()
        after = snapshot(copy)
        run()
        again = snapshot(copy)
        print(out1.strip().splitlines()[-2])

        other_drift, missing, non_han, engine_drift, paddle_drift, untouched_drift = [], [], [], [], [], []
        changed_pages = 0
        for name, old in before.items():
            o, n = old["record"], after[name]["record"]
            if {k: v for k, v in o.items() if k != "pages"} != {k: v for k, v in n.items() if k != "pages"}:
                other_drift.append(name)
            rec_changed = False
            for op, np_ in zip(o.get("pages", []), n.get("pages", [])):
                where = f"{o['doc_id']}/{op.get('page_id')}"
                if {k: v for k, v in op.items() if k != "l1_ocr"} != {k: v for k, v in np_.items() if k != "l1_ocr"}:
                    other_drift.append(where)
                if op.get("l1_ocr") == np_.get("l1_ocr"):
                    continue
                rec_changed = True
                changed_pages += 1
                l1 = np_["l1_ocr"]
                if not (op.get("l1_ocr") or {}).get("engines"):
                    other_drift.append(f"{where}: đổi L1 trang không có engine")
                if REQUIRED - set(l1):
                    missing.append(where)
                if any(ch not in "\n" and han_only(ch) == "" for ch in l1.get("voted_text") or ""):
                    non_han.append(where)
                oe = (op.get("l1_ocr") or {}).get("engines") or {}
                for eng, entry in l1.get("engines", {}).items():
                    if eng == "paddle_v6":
                        if lines_of(entry.get("text")) != lines_of((oe.get(eng) or {}).get("text")):
                            paddle_drift.append(where)
                    elif (entry.get("text") or "") != ((oe.get(eng) or {}).get("text") or ""):
                        engine_drift.append(f"{where}:{eng}")
            if not rec_changed and old["bytes"] != after[name]["bytes"]:
                untouched_drift.append(name)

        print(f"  [info] {changed_pages} trang đổi L1")
        check(not other_drift, "1. Chỉ l1_ocr của trang có engine đổi", "; ".join(other_drift[:5]))
        check(not untouched_drift, "1. Record không đổi giữ nguyên từng byte", ", ".join(untouched_drift[:5]))
        check(not missing, "2. L1 mới đủ trường schema 2", ", ".join(missing[:5]))
        check(not non_han, "2. voted_text chỉ chữ Hán + xuống dòng", ", ".join(non_han[:5]))
        check(not engine_drift, "3. Text engine (trừ paddle) không đổi", ", ".join(engine_drift[:5]))
        check(not paddle_drift, "3. Paddle giữ đúng tập dòng", ", ".join(paddle_drift[:5]))
        check(all(after[k]["bytes"] == again[k]["bytes"] for k in after), "4. Ghi lần 2 không đổi gì")
        try:
            import jsonschema
        except ImportError:
            check(False, "5. Schema", "thiếu jsonschema")
        else:
            v = jsonschema.Draft7Validator(json.loads(SCHEMA.read_text(encoding="utf-8")))
            eb = sum(len(list(v.iter_errors(x["record"]))) for x in before.values())
            ea = sum(len(list(v.iter_errors(x["record"]))) for x in after.values())
            check(ea <= eb, "5. Schema không thêm lỗi", f"trước={eb}, sau={ea}")

    print("\nKẾT QUẢ: " + ("ĐẠT" if not failures else "HỎNG: " + ", ".join(failures)))
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
