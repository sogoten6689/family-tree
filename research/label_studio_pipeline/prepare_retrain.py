"""Chuẩn bị dữ liệu để HUẤN LUYỆN LẠI NER sau khi người soát thêm cây — một lệnh, tái lập được.

Các bước (mỗi bước ghi vào ``manifest.json``):
  1. Gộp ``--human-dir`` (cây đã soát trước đó) với ``--new-dir`` (cây mới soát, xuất bằng export_ls_gold.py);
     trùng mã cây thì bản MỚI thắng.
  2. Làm sạch bằng ``clean_gold`` (không sửa bản gốc); dừng nếu có lỗi kiểm tra offset.
  3. Bỏ tài liệu trùng văn bản (giữ cây mã nhỏ nhất) — tránh rò rỉ train/test.
  4. Chia K lượt kiểm chéo THEO CÂY (``export_cv_folds.plan_folds``) → ``vi_cv<K>.zip``.
  5. Chia bản cuối (dev ≈ 12% cây, tối thiểu 3, không có test) → ``vi_final.zip``.
Đầu ra đặt thẳng vào thư mục sẽ upload lên Drive cùng ``train_ner.py`` và notebook ở ``research/notebooks/``.

    python -m label_studio_pipeline.prepare_retrain --human-dir <v1_human> --new-dir <cây mới> --output-dir <dir>
"""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import sys
import zipfile
from pathlib import Path
from typing import Optional

from label_studio_pipeline import clean_gold
from label_studio_pipeline.export_conll import DEFAULT_MAX_TOKENS, export_files
from label_studio_pipeline.export_cv_folds import plan_folds


def _tree_dirs(base: Optional[Path]) -> dict[str, Path]:
    if base is None or not base.exists():
        return {}
    return {p.name: p for p in sorted(base.iterdir()) if p.is_dir() and (p / "gold.training.json").exists()}


def merge_sources(human_dir: Path, new_dir: Optional[Path], work: Path) -> tuple[Path, dict]:
    old, new = _tree_dirs(human_dir), _tree_dirs(new_dir)
    merged = work / "merged"
    shutil.rmtree(merged, ignore_errors=True)
    for name, src in {**old, **new}.items():  # new ghi đè old
        (merged / name).mkdir(parents=True)
        shutil.copy(src / "gold.training.json", merged / name / "gold.training.json")
    return merged, {"from_human_dir": len(old), "from_new_dir": len(new), "overridden": sorted(set(old) & set(new)), "total": len({**old, **new})}


def drop_duplicates(cleaned: Path, duplicate_of: dict[str, int]) -> list[str]:
    dropped = []
    for dup in sorted(duplicate_of, key=int):
        shutil.rmtree(cleaned / str(dup), ignore_errors=True)
        dropped.append(str(dup))
    return dropped


def final_split(ids: list[str], seed: int = 42) -> tuple[list[str], list[str]]:
    import random

    ordered = sorted(ids)
    random.Random(seed).shuffle(ordered)
    n_dev = max(3, round(0.12 * len(ordered)))
    return sorted(ordered[n_dev:]), sorted(ordered[:n_dev])


def _write_split(cleaned: Path, ids: list[str], out: Path, name: str, max_tokens: int) -> None:
    out.mkdir(parents=True, exist_ok=True)
    export_files([cleaned / t / "gold.training.json" for t in ids], output=out / f"{name}.conll", unit="word",
                 line_breaks="auto", misaligned="snap", max_tokens=max_tokens, sep="\t")


def _zip_dir(src: Path, zip_path: Path) -> None:
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
        for f in sorted(src.rglob("*")):
            if f.is_file() and not f.name.endswith(".stats.json"):
                zf.write(f, f.relative_to(src.parent))


def prepare(human_dir: Path, new_dir: Optional[Path], output_dir: Path, *, folds: int = 5, seed: int = 42,
            max_tokens: int = DEFAULT_MAX_TOKENS, progress=print) -> dict:
    output_dir.mkdir(parents=True, exist_ok=True)
    work = output_dir / "_work"
    merged, merge_info = merge_sources(human_dir, new_dir, work)
    cleaned = work / "cleaned"
    shutil.rmtree(cleaned, ignore_errors=True)
    report = clean_gold.clean_directory(merged, cleaned, progress=lambda *_: None)
    if report["totals"].get("verify_failed_docs"):
        raise SystemExit(f"{report['totals']['verify_failed_docs']} tài liệu lỗi offset sau làm sạch — xem {cleaned/'clean_report.json'}")
    dropped = drop_duplicates(cleaned, report["duplicate_of"])
    ids = sorted(p.name for p in cleaned.iterdir() if p.is_dir())

    cv_root = work / f"vi_cv{folds}"
    shutil.rmtree(cv_root, ignore_errors=True)
    fold_plan = plan_folds(ids, folds, seed)
    for f in fold_plan:
        for split in ("train", "dev", "test"):
            _write_split(cleaned, f[split], cv_root / f"fold{f['fold']}", split, max_tokens)
    (cv_root / "folds.json").write_text(json.dumps({"seed": seed, "folds": fold_plan}, indent=2), encoding="utf-8")

    train, dev = final_split(ids, seed)
    final_root = work / "vi_final"
    shutil.rmtree(final_root, ignore_errors=True)
    _write_split(cleaned, train, final_root, "train", max_tokens)
    _write_split(cleaned, dev, final_root, "dev", max_tokens)
    (final_root / "split.json").write_text(json.dumps({"train": train, "dev": dev}), encoding="utf-8")

    _zip_dir(cv_root, output_dir / f"vi_cv{folds}.zip")
    _zip_dir(final_root, output_dir / "vi_final.zip")
    manifest = {
        "seed": seed, "folds": folds, "clean_version": clean_gold.CLEAN_VERSION, "merge": merge_info,
        "duplicates_dropped": dropped, "trees_used": len(ids), "tree_ids": ids,
        "final": {"train": len(train), "dev": len(dev)},
        "cleaning_totals": report["totals"],
        "input_sha256": hashlib.sha256(b"".join((cleaned / t / "gold.training.json").read_bytes() for t in ids)).hexdigest(),
    }
    (output_dir / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    shutil.copy(cleaned / "clean_report.json", output_dir / "clean_report.json")
    progress(f"{len(ids)} cây ({len(dropped)} trùng bị bỏ) → {output_dir}")
    return manifest


def main(argv: Optional[list[str]] = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--human-dir", type=Path, required=True)
    ap.add_argument("--new-dir", type=Path)
    ap.add_argument("--output-dir", type=Path, required=True)
    ap.add_argument("--folds", type=int, default=5)
    ap.add_argument("--seed", type=int, default=42)
    args = ap.parse_args(argv)
    prepare(args.human_dir, args.new_dir, args.output_dir, folds=args.folds, seed=args.seed)
    return 0


if __name__ == "__main__":
    sys.exit(main())
