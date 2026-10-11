"""Gợi ý nhãn bằng model NER đã huấn luyện (PhoBERT ONNX) cho các cây CHƯA được người soát.

Không gọi mạng, không gọi API tốn tiền: chạy model cục bộ rồi ghi
  - ``tasks.json``  : task Label Studio có ``predictions`` (mỗi vùng kèm ``score`` = độ tin cậy) — anh tự Import;
  - ``priority.csv``: cây nào nên soát trước (độ lệch giữa model và nhãn Gemini hiện có, càng lệch càng nhiều việc/giá trị).

    python -m label_studio_pipeline.prelabel_with_model --model-dir <thư mục model> \
        --docs-dir <gemini_review/v2> --exclude-dir <v1_human> --output-dir <dir> [--limit N]

Model huấn luyện trên 22/25 cây người soát, KHÔNG thấy các cây Gemini nên dự đoán ở đây không bị rò rỉ.
Nhãn ra là gợi ý (F1 kiểm chéo ≈ 0,54): người soát phải xem lại, đặc biệt PER_NAME và LOC.
"""

from __future__ import annotations

import argparse
import csv
import importlib.util
import json
import sys
from pathlib import Path
from typing import Callable, Iterable, Optional

import uuid

# Cấu trúc vùng nhãn khớp ls_importer.py (ENTITY_LABEL_CONTROL="label", TEXT_OBJECT="text"); không import ls_importer
# để chạy được khi chưa cài label_studio_sdk.
ENTITY_LABEL_CONTROL = "label"
TEXT_OBJECT = "text"


def _new_region_id(prefix: str = "ent") -> str:
    return f"{prefix}_{uuid.uuid4().hex[:12]}"


def _build_label_region(*, region_id: str, start: int, end: int, span_text: str, label: str, score: float) -> dict:
    return {
        "id": region_id, "from_name": ENTITY_LABEL_CONTROL, "to_name": TEXT_OBJECT, "type": "labels",
        "value": {"start": start, "end": end, "text": span_text, "labels": [label], "score": score},
    }

MODEL_VERSION = "phobert-ner-onnx-v1"
_NER_FILE = Path(__file__).resolve().parents[2] / "nlp_family_extractor" / "app" / "ner" / "phobert_onnx.py"


def load_ner_model(model_dir: Path):
    spec = importlib.util.spec_from_file_location("phobert_onnx_standalone", _NER_FILE)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module  # dataclass cần module đã đăng ký
    spec.loader.exec_module(module)
    return module.NerModel(model_dir)


def build_task(doc: dict, entities: list[dict], tree_id: Optional[int] = None) -> dict:
    """Task Label Studio: văn bản + một prediction; mỗi vùng mang độ tin cậy của model."""
    text = doc["text"]
    result = []
    for ent in entities:
        assert text[ent["start"]:ent["end"]] == ent["text"], "offset lệch"
        result.append(_build_label_region(region_id=_new_region_id(), start=ent["start"], end=ent["end"],
                                          span_text=ent["text"], label=ent["label"], score=ent["confidence"]))
    mean = round(sum(e["confidence"] for e in entities) / len(entities), 4) if entities else 0.0
    data = {"text": text, "title": doc.get("title", ""), "source_url": doc.get("source_url", "")}
    if tree_id is not None:
        data["tree_id"] = tree_id
    return {"data": data, "predictions": [{"model_version": MODEL_VERSION, "score": mean, "result": result}]}


def agreement(model_entities: Iterable[dict], other_entities: Iterable[dict]) -> dict:
    """Khớp tuyệt đối (đầu, cuối, nhãn) giữa model và nhãn hiện có."""
    a = {(e["start"], e["end"], e["label"]) for e in model_entities}
    b = {(e["start"], e["end"], e["label"]) for e in other_entities}
    tp = len(a & b)
    p = tp / len(a) if a else 0.0
    r = tp / len(b) if b else 0.0
    f1 = 2 * p * r / (p + r) if p + r else 0.0
    return {"model": len(a), "existing": len(b), "agree": tp, "f1": round(f1, 4)}


def run(model_dir: Path, docs_dir: Path, exclude_dir: Optional[Path], output_dir: Path, limit: Optional[int],
        extract: Optional[Callable[[str], list[dict]]] = None, progress: Callable[[str], None] = print) -> dict:
    extract = extract or load_ner_model(model_dir).extract
    excluded = {p.name for p in exclude_dir.iterdir() if p.is_dir()} if exclude_dir and exclude_dir.exists() else set()
    trees = sorted((p for p in docs_dir.iterdir() if (p / "gold.training.json").exists() and p.name not in excluded),
                   key=lambda p: int(p.name) if p.name.isdigit() else 0)
    if limit:
        trees = trees[:limit]
    tasks, rows = [], []
    for i, tree in enumerate(trees, 1):
        doc = json.loads((tree / "gold.training.json").read_text(encoding="utf-8"))
        entities = extract(doc["text"])
        tid = int(tree.name) if tree.name.isdigit() else None
        tasks.append(build_task(doc, entities, tid))
        ag = agreement(entities, doc.get("entities") or [])
        rows.append({"tree_id": tree.name, "chars": len(doc["text"]), "model_entities": ag["model"], "gemini_entities": ag["existing"],
                     "agree": ag["agree"], "agreement_f1": ag["f1"],
                     "mean_confidence": tasks[-1]["predictions"][0]["score"]})
        if i % 10 == 0:
            progress(f"{i}/{len(trees)}")
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "tasks.json").write_text(json.dumps(tasks, ensure_ascii=False), encoding="utf-8")
    rows.sort(key=lambda r: (r["agreement_f1"], -r["chars"]))  # lệch nhiều nhất lên đầu
    with (output_dir / "priority.csv").open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()) if rows else ["tree_id"])
        w.writeheader()
        w.writerows(rows)
    summary = {"trees": len(tasks), "excluded_human": len(excluded), "model_version": MODEL_VERSION,
               "entities": sum(r["model_entities"] for r in rows)}
    (output_dir / "summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    return summary


def main(argv: Optional[list[str]] = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--model-dir", type=Path, required=True)
    ap.add_argument("--docs-dir", type=Path, required=True)
    ap.add_argument("--exclude-dir", type=Path, help="thư mục cây đã người soát (bỏ qua)")
    ap.add_argument("--output-dir", type=Path, required=True)
    ap.add_argument("--limit", type=int)
    args = ap.parse_args(argv)
    print(json.dumps(run(args.model_dir, args.docs_dir, args.exclude_dir, args.output_dir, args.limit), ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
