"""Export normalized gia phả folders under data/03_derived/gia_pha/."""

from __future__ import annotations

import json
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from label_studio_pipeline.data_layout import (
    DERIVED_GIA_PHA,
    INTERIM_GEMINI_LABELS,
    RAW_VGP_CORPUS,
)
from label_studio_pipeline.corpus_store import load_json, tree_dir
from label_studio_pipeline.import_registry import load_registry
from label_studio_pipeline.text_encoding import build_vocab, fix_text, needs_fix

DEFAULT_SOURCE_DIR = RAW_VGP_CORPUS
DEFAULT_EXPORT_DIR = DERIVED_GIA_PHA
DEFAULT_LABELS_DIR = INTERIM_GEMINI_LABELS

MIN_COVERAGE_GAIN = 0.10

TREE_FILES = (
    ("pha_ky.txt", "pha_ky.txt"),
    ("pha_he.json", "pha_he.json"),
    ("pha_he.txt", "pha_he.txt"),
)


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _read_text_optional(path: Path) -> str | None:
    if not path.is_file():
        return None
    return path.read_text(encoding="utf-8")


def build_metadata(
    *,
    tree_id: int,
    source_dir: Path,
    labels_dir: Path | None = None,
) -> dict[str, Any]:
    """Merge crawl meta, assessment, and label import info into metadata.json."""
    base = tree_dir(source_dir, tree_id)
    meta = load_json(base / "meta.json") or {}
    assessment = load_json(base / "pha_ky.assessment.json")

    metadata: dict[str, Any] = {
        "tree_id": tree_id,
        "lineage_name": meta.get("lineage_name"),
        "title": meta.get("title"),
        "location": meta.get("location"),
        "urls": {
            "giapha": meta.get("giapha_url"),
            "pha_ky": meta.get("pha_ky_url"),
            "pha_he": meta.get("pha_he_url"),
        },
        "stats": {
            "person_count": meta.get("person_count"),
            "family_count": meta.get("family_count"),
            "generation_count": meta.get("generation_count"),
            "pha_ky_char_count": meta.get("pha_ky_char_count"),
            "pha_he_node_count": meta.get("pha_he_node_count"),
        },
        "content_hash": meta.get("content_hash"),
        "source_updated_at": meta.get("updated_at"),
        "exported_at": _now_iso(),
    }

    if assessment:
        metadata["assessment"] = {
            "suitable": assessment.get("suitable"),
            "score": assessment.get("score"),
            "skip_reasons": assessment.get("skip_reasons", []),
            "warnings": assessment.get("warnings", []),
            "metrics": assessment.get("metrics"),
        }

    if labels_dir is not None:
        registry = load_registry(labels_dir)
        import_entry = registry.get("entries", {}).get(str(tree_id))
        labels_base = labels_dir / str(tree_id)
        entities = load_json(labels_base / "pha_ky.entities.json")
        if import_entry or entities:
            metadata["labeling"] = {
                "imported": import_entry.get("status") == "imported" if import_entry else False,
                "imported_at": import_entry.get("imported_at") if import_entry else None,
                "project_id": import_entry.get("project_id") if import_entry else None,
                "entity_count": len(entities.get("entities", [])) if entities else None,
                "relation_count": len(entities.get("relations", [])) if entities else None,
            }

    return metadata


def _fix_label_files(label_dst: Path, raw_text: str, fixed_text: str) -> dict[str, Any]:
    """Nhãn Gemini tạo trên văn bản lỗi mã chứa chuỗi lỗi mã. Khi sửa giữ nguyên độ dài (TCVN3 1→1 ký tự), lấy lại chuỗi
    tại đúng vị trí trong văn bản đã sửa: ls_task.json theo offset; entities.json (chỉ có chuỗi) theo vị trí xuất hiện
    đầu tiên trong văn bản gốc. cross_check.json không tính lại được ở đây → đánh dấu cũ."""
    assert len(raw_text) == len(fixed_text)
    report: dict[str, Any] = {}
    task_path = label_dst / "ls_task.json"
    if task_path.is_file():
        task = json.loads(task_path.read_text(encoding="utf-8"))
        if task.get("data", {}).get("text") == raw_text:
            task["data"]["text"] = fixed_text
            n = 0
            for pred in task.get("predictions", []):
                for r in pred.get("result", []):
                    v = r.get("value", {})
                    if "start" in v and "end" in v and "text" in v:
                        v["text"] = fixed_text[v["start"]:v["end"]]
                        n += 1
            task_path.write_text(json.dumps(task, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
            report["ls_task_regions"] = n
        else:
            report["ls_task"] = "văn bản task khác pha_ky gốc — giữ nguyên"
    ent_path = label_dst / "entities.json"
    if ent_path.is_file():
        ents = json.loads(ent_path.read_text(encoding="utf-8"))
        fixed = missing = 0
        for e in ents.get("entities", []):
            s = e.get("text")
            i = raw_text.find(s) if s else -1
            if i < 0:
                missing += 1
                continue
            new = fixed_text[i:i + len(s)]
            if new != s:
                e["text"] = new
                fixed += 1
        ent_path.write_text(json.dumps(ents, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        report.update(entities_fixed=fixed, entities_not_found=missing)
    if (label_dst / "cross_check.json").is_file():
        report["cross_check"] = "cũ (tính trên văn bản lỗi mã)"
    return report


def export_tree(
    tree_id: int,
    *,
    source_dir: Path,
    export_dir: Path,
    labels_dir: Path | None = None,
    include_labels: bool = True,
    vocab: set[str] | None = None,
) -> dict[str, Any]:
    """Export one tree into export_dir/{tree_id}/ with standardized filenames.

    ``vocab`` (âm tiết của các Phả ký sạch) bật sửa bảng mã cũ TCVN3/VNI cho pha_ky.txt; bản gốc giữ ở pha_ky.raw.txt.
    Cây có nhãn mà việc sửa làm đổi độ dài văn bản (VNI) thì KHÔNG sửa, vì offset nhãn tính trên văn bản gốc."""
    src = tree_dir(source_dir, tree_id)
    if not (src / "pha_ky.txt").is_file():
        raise FileNotFoundError(f"Missing source pha_ky.txt for tree_id={tree_id}")

    dst = export_dir / str(tree_id)
    dst.mkdir(parents=True, exist_ok=True)

    copied: list[str] = []
    for src_name, dst_name in TREE_FILES:
        src_path = src / src_name
        if src_path.is_file():
            shutil.copy2(src_path, dst / dst_name)
            copied.append(dst_name)

    raw_copy = dst / "pha_ky.raw.txt"
    if raw_copy.is_file():
        raw_copy.unlink()  # chạy lại export: không để bản gốc cũ khi lần này không cần sửa
    encoding_report = None
    if vocab is not None:
        text = (dst / "pha_ky.txt").read_text(encoding="utf-8")
        fixed, encoding_report = fix_text(text, vocab)
        if encoding_report["detected"] == "legacy":
            has_labels = include_labels and labels_dir is not None and (labels_dir / str(tree_id)).is_dir()
            # Sửa thật: tăng ≥ 0,10, hoặc (tài liệu trộn, phần lỗi nhỏ) sau sửa ≥ 0,90 và tăng > 0,02.
            # Kiểu mojibake khác (vd UTF-8 mã hoá hai lần) chỉ tăng chút ít và vẫn thấp → không sửa.
            before, after = encoding_report["vocab_coverage_before"], encoding_report["vocab_coverage_after"]
            improved = after - before >= MIN_COVERAGE_GAIN or (after >= 0.90 and after - before > 0.02)
            if not improved:
                encoding_report["applied"], encoding_report["reason"] = False, "sửa không cải thiện rõ độ phủ từ vựng"
            elif has_labels and encoding_report["length_changed"]:
                encoding_report["applied"], encoding_report["reason"] = False, "có nhãn và sửa làm lệch offset (VNI)"
            else:
                raw_copy.write_text(text, encoding="utf-8")
                (dst / "pha_ky.txt").write_text(fixed, encoding="utf-8")
                encoding_report["applied"] = True
                copied.append("pha_ky.raw.txt")

    assessment_src = src / "pha_ky.assessment.json"
    if assessment_src.is_file():
        shutil.copy2(assessment_src, dst / "assessment.json")
        copied.append("assessment.json")

    if include_labels and labels_dir is not None:
        label_src = labels_dir / str(tree_id)
        if label_src.is_dir():
            label_dst = dst / "labels"
            label_dst.mkdir(exist_ok=True)
            for name in ("pha_ky.entities.json", "pha_ky.ls_task.json", "import_status.json", "cross_check.json"):
                path = label_src / name
                if path.is_file():
                    out_name = name.replace("pha_ky.", "")
                    shutil.copy2(path, label_dst / out_name)
                    copied.append(f"labels/{out_name}")

    # Nhãn vừa copy (tạo trên văn bản gốc) phải theo văn bản đã sửa — làm SAU bước copy nhãn
    if encoding_report and encoding_report.get("applied") and (dst / "labels").is_dir():
        if not encoding_report["length_changed"]:
            encoding_report["labels"] = _fix_label_files(dst / "labels", text, fixed)
        else:
            encoding_report["labels"] = "độ dài đổi — nhãn trong labels/ còn theo văn bản gốc (pha_ky.raw.txt)"

    metadata = build_metadata(tree_id=tree_id, source_dir=source_dir, labels_dir=labels_dir)
    if encoding_report and encoding_report["detected"] == "legacy":
        metadata["text_encoding"] = encoding_report
    (dst / "metadata.json").write_text(
        json.dumps(metadata, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    copied.append("metadata.json")

    return {
        "tree_id": tree_id,
        "export_dir": str(dst),
        "files": copied,
        "lineage_name": metadata.get("lineage_name"),
        "text_encoding": metadata.get("text_encoding"),
    }


def _encoding_vocab(source_dir: Path, tree_ids: list[int], min_clean: int = 20) -> set[str]:
    """Âm tiết của các Phả ký sạch trong lô export; lô quá nhỏ thì lấy cả kho nguồn."""
    def clean_texts(paths):
        for p in paths:
            if p.is_file():
                t = p.read_text(encoding="utf-8")
                if not needs_fix(t):
                    yield t

    batch = list(clean_texts(tree_dir(source_dir, t) / "pha_ky.txt" for t in tree_ids))
    if len(batch) < min_clean:
        batch = list(clean_texts(source_dir.glob("*/pha_ky.txt")))
    return build_vocab(batch)


def export_trees(
    tree_ids: list[int],
    *,
    source_dir: Path = DEFAULT_SOURCE_DIR,
    export_dir: Path = DEFAULT_EXPORT_DIR,
    labels_dir: Path | None = DEFAULT_LABELS_DIR,
    include_labels: bool = True,
    fix_encoding: bool = True,
) -> dict[str, Any]:
    """Export many trees and write index.json at export root."""
    export_dir.mkdir(parents=True, exist_ok=True)
    exported: list[dict[str, Any]] = []
    errors: list[dict[str, Any]] = []
    vocab = _encoding_vocab(source_dir, tree_ids) if fix_encoding else None

    for tree_id in tree_ids:
        try:
            exported.append(
                export_tree(
                    tree_id,
                    source_dir=source_dir,
                    export_dir=export_dir,
                    labels_dir=labels_dir,
                    include_labels=include_labels,
                    vocab=vocab,
                ),
            )
        except (OSError, FileNotFoundError) as exc:
            errors.append({"tree_id": tree_id, "error": str(exc)})

    index = {
        "description": "Gia phả export — mỗi thư mục con = 1 tree_id từ vietnamgiapha.com",
        "layout": {
            "metadata.json": "Metadata gia phả (URLs, stats, assessment, labeling)",
            "pha_ky.txt": "Phả ký — văn bản Quốc ngữ (đã sửa bảng mã cũ TCVN3/VNI nếu phát hiện)",
            "pha_ky.raw.txt": "Phả ký gốc trước khi sửa bảng mã (chỉ có khi đã sửa; xem metadata.text_encoding)",
            "pha_he.json": "Phả hệ — sơ đồ structured (nodes + relationships)",
            "pha_he.txt": "Phả hệ dạng text phẳng (optional)",
            "assessment.json": "Đánh giá chất lượng Phả ký trước Gemini",
            "labels/": "Gemini pre-annotation + import status (optional)",
        },
        "source_dir": str(source_dir),
        "export_dir": str(export_dir),
        "exported_count": len(exported),
        "encoding_fixed": [item["tree_id"] for item in exported if (item.get("text_encoding") or {}).get("applied")],
        "error_count": len(errors),
        "tree_ids": [item["tree_id"] for item in exported],
        "trees": exported,
        "errors": errors,
        "generated_at": _now_iso(),
    }
    (export_dir / "index.json").write_text(
        json.dumps(index, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return index
