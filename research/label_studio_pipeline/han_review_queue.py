"""Chia nhãn máy Hán thành các lô để người DUYỆT (approve) trong Label Studio, trang nghi ngờ xem kỹ trước.

Mỗi trang được gắn cờ nếu: không có thực thể nào; có thực thể không khớp chuỗi; OCR kém đồng thuận (agreement thấp);
có ký tự ngoài BMP (nhãn có thể lệch); quá nhiều thực thể bất thường; hoặc nằm trong tập test (held_out).
Trang không cờ = "sạch": chỉ cần lướt xem rồi duyệt. Trang thuộc tập test KHÔNG đưa vào lô huấn luyện.

Đầu ra:
  queue.csv           — mọi trang, cờ, mức ưu tiên (flagged trước), lô
  batches/batch_NNN.json — task Label Studio (có predictions) mỗi lô `--batch-size` trang
  summary.json        — số trang sạch/nghi ngờ/test

    python -m label_studio_pipeline.han_review_queue --gold-dir <gold> --manifest <han_full_v1/manifest.csv> --held-out <han_test_v1/held_out.json> --out <dir>
"""
from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path
from typing import Any, Dict, List, Optional

from label_studio_pipeline.build_han_pilot import has_non_bmp
from label_studio_pipeline.han_llm_prelabel import to_ls_task

LOW_AGREEMENT = 0.35
MAX_ENTITIES_PER_100_CHARS = 20.0


def flags_for(doc: Dict[str, Any], agreement: Optional[float], held_out: bool) -> List[str]:
    flags = []
    ents = doc["entities"]
    if held_out:
        flags.append("tap_test")
    if not ents:
        flags.append("khong_thuc_the")
    if doc.get("stats", {}).get("unmatched", 0) > 0:
        flags.append("khong_khop_chuoi")
    if agreement is not None and agreement < LOW_AGREEMENT:
        flags.append("ocr_kem_dong_thuan")
    if has_non_bmp(doc["text"]):
        flags.append("ngoai_bmp")
    if doc["text"] and 100.0 * len(ents) / len(doc["text"]) > MAX_ENTITIES_PER_100_CHARS:
        flags.append("qua_nhieu_thuc_the")
    return flags


def build(gold_dir: Path, manifest: Path, held_out_path: Optional[Path], out_dir: Path, batch_size: int = 50) -> Dict[str, Any]:
    agreement: Dict[str, Optional[float]] = {}
    with manifest.open(encoding="utf-8") as fh:
        for row in csv.DictReader(fh):
            agreement[f"han-{row['scan_id']}-p{int(row['page_number']):03d}"] = float(row["agreement"]) if row["agreement"] else None
    held_out = set(json.loads(held_out_path.read_text(encoding="utf-8"))) if held_out_path and held_out_path.exists() else set()
    rows = []
    for path in sorted(gold_dir.glob("*.json")):
        doc = json.loads(path.read_text(encoding="utf-8"))
        flags = flags_for(doc, agreement.get(doc["doc_id"]), doc["doc_id"] in held_out)
        rows.append({"doc": doc, "flags": flags, "agreement": agreement.get(doc["doc_id"])})
    trainable = [r for r in rows if "tap_test" not in r["flags"]]
    # Nghi ngờ trước (nhiều cờ nhất trước), sạch sau; ổn định theo doc_id.
    trainable.sort(key=lambda r: (-len(r["flags"]), r["doc"]["doc_id"]))
    (out_dir / "batches").mkdir(parents=True, exist_ok=True)
    with (out_dir / "queue.csv").open("w", encoding="utf-8", newline="") as fh:
        writer = csv.writer(fh)
        writer.writerow(["batch", "doc_id", "scan_id", "page_number", "flags", "agreement", "entities", "relations"])
        for index, r in enumerate(trainable):
            d = r["doc"]
            batch = index // batch_size + 1
            writer.writerow([batch, d["doc_id"], d["provenance"]["scan_id"], d["provenance"]["page_number"], "|".join(r["flags"]),
                             "" if r["agreement"] is None else round(r["agreement"], 3), len(d["entities"]), len(d["relations"])])
        for r in rows:
            if "tap_test" in r["flags"]:
                d = r["doc"]
                writer.writerow(["TEST", d["doc_id"], d["provenance"]["scan_id"], d["provenance"]["page_number"], "|".join(r["flags"]),
                                 "" if r["agreement"] is None else round(r["agreement"], 3), len(d["entities"]), len(d["relations"])])
    for start in range(0, len(trainable), batch_size):
        chunk = trainable[start : start + batch_size]
        (out_dir / "batches" / f"batch_{start // batch_size + 1:03d}.json").write_text(
            json.dumps([to_ls_task(r["doc"]) for r in chunk], ensure_ascii=False, indent=1), encoding="utf-8")
    flagged = sum(1 for r in trainable if r["flags"])
    summary = {"pages_total": len(rows), "test_pages": len(rows) - len(trainable), "to_review": len(trainable), "flagged": flagged,
               "clean": len(trainable) - flagged, "batches": (len(trainable) + batch_size - 1) // batch_size, "batch_size": batch_size}
    (out_dir / "summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    return summary


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--gold-dir", type=Path, required=True)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--held-out", type=Path)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--batch-size", type=int, default=50)
    args = parser.parse_args()
    print(json.dumps(build(args.gold_dir, args.manifest, args.held_out, args.out, args.batch_size), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
