"""Phân tích NGOẠI TUYẾN xác suất dự đoán (probs.json do ``train_ner --save-probs`` ghi) — không cần GPU/torch.

Thử ba cách tăng F1 mà không huấn luyện lại:
  1. GỘP model: lấy trung bình xác suất của nhiều cấu hình (ensemble).
  2. NGƯỠNG tin cậy: chỉ gán thực thể khi P(không-O) ≥ t (tăng precision, giảm recall); có thể đặt ngưỡng riêng từng nhãn.
  3. Sửa BIO: ``I-X`` mồ côi → ``B-X``.
Để không tự lừa mình, ngưỡng được CHỌN trên 4 lượt và ĐÁNH GIÁ trên lượt còn lại (lồng nhau, xoay vòng 5 lượt).

    python -m label_studio_pipeline.analyze_probs --run base=<dir chứa fold0_probs.json…> --run xlmr=<dir> --output report.json
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Optional, Sequence

from label_studio_pipeline.train_ner import ENTITY_LABELS, LABEL_LIST, bio_to_spans, entity_prf

O_ID = LABEL_LIST.index("O")
THRESHOLDS = [0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9]


def load_run(run_dir: Path, folds: int = 5) -> list[list[dict]]:
    """[fold][sentence] = {words, gold, probs} của tập test."""
    out = []
    for k in range(folds):
        data = json.loads((Path(run_dir) / f"fold{k}_probs.json").read_text(encoding="utf-8"))
        out.append(data["test"])
    return out


def average_runs(runs: Sequence[list[list[dict]]], weights: Optional[Sequence[float]] = None) -> list[list[dict]]:
    """Trung bình xác suất giữa các run; kiểm tra các run khớp câu/từ."""
    weights = list(weights) if weights else [1.0] * len(runs)
    total = sum(weights)
    merged = []
    for k, folds in enumerate(zip(*runs)):
        sents = []
        for sent_variants in zip(*folds):
            base = sent_variants[0]
            for v in sent_variants[1:]:
                if v["words"] != base["words"]:
                    raise ValueError(f"fold{k}: các run không cùng câu/từ")
            probs = [[sum(w * v["probs"][i][j] for w, v in zip(weights, sent_variants)) / total for j in range(len(LABEL_LIST))]
                     for i in range(len(base["words"]))]
            sents.append({"words": base["words"], "gold": base["gold"], "probs": probs})
        merged.append(sents)
    return merged


def decode_word(p: Sequence[float], t_by_label: dict[str, float]) -> str:
    """Chọn nhãn không-O tốt nhất; chỉ gán nếu xác suất của THỰC THỂ đó (B+I cùng loại) ≥ ngưỡng nhãn, ngược lại O."""
    best, best_score = "O", 0.0
    for lab in ENTITY_LABELS:
        score = p[LABEL_LIST.index(f"B-{lab}")] + p[LABEL_LIST.index(f"I-{lab}")]
        if score > best_score:
            best, best_score = lab, score
    if best == "O" or best_score < t_by_label.get(best, 0.5):
        return "O"
    return f"B-{best}" if p[LABEL_LIST.index(f"B-{best}")] >= p[LABEL_LIST.index(f"I-{best}")] else f"I-{best}"


def repair_bio(tags: list[str]) -> list[str]:
    out, prev = [], "O"
    for t in tags:
        if t.startswith("I-") and prev[2:] != t[2:]:
            t = "B-" + t[2:]
        out.append(t)
        prev = t
    return out


def predict(sentences: list[dict], t_by_label: dict[str, float]) -> list[list[str]]:
    return [repair_bio([decode_word(p, t_by_label) for p in s["probs"]]) for s in sentences]


def score(folds: list[list[dict]], idx: Sequence[int], t_by_label: dict[str, float]) -> dict:
    gold, pred = [], []
    for k in idx:
        gold += [s["gold"] for s in folds[k]]
        pred += predict(folds[k], t_by_label)
    return entity_prf(gold, pred)


def tune_per_label(folds: list[list[dict]], train_idx: Sequence[int]) -> dict[str, float]:
    """Chọn ngưỡng riêng từng nhãn bằng tìm tọa độ (2 vòng) trên các lượt train_idx."""
    t = {lab: 0.5 for lab in ENTITY_LABELS}
    for _ in range(2):
        for lab in ENTITY_LABELS:
            best_t, best_f = t[lab], -1.0
            for cand in THRESHOLDS:
                t2 = {**t, lab: cand}
                f = score(folds, train_idx, t2)["micro"]["f1"]
                if f > best_f + 1e-9:
                    best_t, best_f = cand, f
            t[lab] = best_t
    return t


def evaluate(folds: list[list[dict]]) -> dict:
    n = len(folds)
    all_idx = list(range(n))
    argmax_like = {lab: 0.5 for lab in ENTITY_LABELS}
    report = {"pooled_default": score(folds, all_idx, argmax_like)["micro"]}
    # ngưỡng chung (toàn cục): chọn trên n-1 lượt, đánh giá lượt còn lại
    def tune_global(tr):
        best = max(THRESHOLDS, key=lambda c: score(folds, tr, {lab: c for lab in ENTITY_LABELS})["micro"]["f1"])
        return {lab: best for lab in ENTITY_LABELS}

    for name, tuner in (("global", tune_global), ("per_label", lambda tr: tune_per_label(folds, tr))):
        gold, pred, chosen = [], [], []
        for k in all_idx:
            t = tuner([i for i in all_idx if i != k])
            chosen.append(t)
            gold += [s["gold"] for s in folds[k]]
            pred += predict(folds[k], t)
        report[f"nested_{name}"] = entity_prf(gold, pred)
        report[f"nested_{name}_thresholds"] = chosen
    return report


def main(argv: Optional[list[str]] = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--run", action="append", required=True, metavar="TÊN=THƯ_MỤC")
    ap.add_argument("--output", type=Path, required=True)
    args = ap.parse_args(argv)
    runs = {}
    for spec in args.run:
        name, _, d = spec.partition("=")
        runs[name] = load_run(Path(d))
    result = {"single": {name: evaluate(f) for name, f in runs.items()}}
    names = list(runs)
    if len(names) > 1:
        result["ensemble_all"] = evaluate(average_runs([runs[n] for n in names]))
        for i in range(len(names)):
            for j in range(i + 1, len(names)):
                result[f"ensemble_{names[i]}+{names[j]}"] = evaluate(average_runs([runs[names[i]], runs[names[j]]]))
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    for key, rep in ({**{f"single:{n}": r for n, r in result["single"].items()}, **{k: v for k, v in result.items() if k != "single"}}).items():
        print(f"{key:36s} mặc định {rep['pooled_default']['f1']:.3f} | ngưỡng chung {rep['nested_global']['micro']['f1']:.3f} | ngưỡng từng nhãn {rep['nested_per_label']['micro']['f1']:.3f}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
