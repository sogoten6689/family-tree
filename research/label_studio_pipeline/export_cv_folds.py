"""Chia gold người soát thành K lượt kiểm chéo THEO CÂY (không bao giờ tách một cây qua hai tập) rồi xuất CoNLL.

Mỗi lượt k: test = nhóm k; dev = 3 cây đầu của nhóm k+1; train = phần còn lại. Mọi cây làm test đúng một lần,
nên F1 gộp 25 cây tin cậy hơn nhiều so với một tập test 5 cây.

    python -m label_studio_pipeline.export_cv_folds --human-dir <v1_human> --output <dir> [--folds 5 --seed 42]
"""

from __future__ import annotations

import argparse
import json
import random
import sys
from pathlib import Path
from typing import Optional

from label_studio_pipeline.export_conll import DEFAULT_MAX_TOKENS, export_files

DEV_TREES = 3


def plan_folds(tree_ids: list[str], k: int, seed: int) -> list[dict]:
    if len(tree_ids) < k * 2:
        raise ValueError(f"{len(tree_ids)} cây quá ít cho {k} lượt")
    ids = sorted(tree_ids)
    random.Random(seed).shuffle(ids)
    groups = [ids[i::k] for i in range(k)]
    folds = []
    for i in range(k):
        test = groups[i]
        dev = groups[(i + 1) % k][:DEV_TREES]
        used = set(test) | set(dev)
        folds.append({"fold": i, "test": sorted(test), "dev": sorted(dev), "train": sorted(t for t in ids if t not in used)})
    return folds


def main(argv: Optional[list[str]] = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--human-dir", type=Path, required=True)
    ap.add_argument("--output", type=Path, required=True)
    ap.add_argument("--folds", type=int, default=5)
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--max-tokens", type=int, default=DEFAULT_MAX_TOKENS)
    args = ap.parse_args(argv)

    ids = [p.parent.name for p in args.human_dir.glob("*/gold.training.json")]
    folds = plan_folds(ids, args.folds, args.seed)
    for f in folds:
        out = args.output / f"fold{f['fold']}"
        out.mkdir(parents=True, exist_ok=True)
        for split in ("train", "dev", "test"):
            export_files([args.human_dir / t / "gold.training.json" for t in f[split]], output=out / f"{split}.conll",
                         unit="word", line_breaks="auto", misaligned="snap", max_tokens=args.max_tokens, sep="\t")
    (args.output / "folds.json").write_text(json.dumps({"seed": args.seed, "folds": folds}, indent=2), encoding="utf-8")
    print(f"{len(ids)} cây → {args.folds} lượt tại {args.output}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
