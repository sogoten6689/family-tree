"""Generate synthetic Phả ký prose + gold labels from pha_he diagrams."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Literal

from label_studio_pipeline.gemini_extractor import Entity, ExtractionResult, Relation
from label_studio_pipeline.gold_builder import build_gold_ls_result, to_training_record

RelationType = Literal["FATHER_OF", "MOTHER_OF", "SPOUSE"]
ORDER_WORDS = (
    "nhất",
    "nhì",
    "ba",
    "tư",
    "năm",
    "sáu",
    "bảy",
    "tám",
    "chín",
    "mười",
)


@dataclass
class _Span:
    start: int
    end: int
    text: str
    label: str


@dataclass
class _Builder:
    parts: list[str] = field(default_factory=list)
    spans: list[_Span] = field(default_factory=list)
    relations: list[Relation] = field(default_factory=list)
    _length: int = 0

    def _append_raw(self, text: str) -> tuple[int, int]:
        start = self._length
        self.parts.append(text)
        self._length += len(text)
        return start, self._length

    def newline(self) -> None:
        if self.parts and not self.parts[-1].endswith("\n"):
            self._append_raw("\n")

    def blank_line(self) -> None:
        self.newline()
        self._append_raw("\n")

    def add_labeled_span(self, text: str, label: str) -> tuple[int, int]:
        start, end = self._append_raw(text)
        self.spans.append(_Span(start=start, end=end, text=text, label=label))
        return start, end

    def add_plain(self, text: str) -> None:
        self._append_raw(text)

    def add_relation(self, rel_type: RelationType, head: str, tail: str) -> None:
        self.relations.append(
            {
                "type": rel_type,
                "head": head,
                "tail": tail,
                "head_label": "PER_NAME",
                "tail_label": "PER_NAME",
            }
        )

    def text(self) -> str:
        return "".join(self.parts)

    def extraction(self) -> ExtractionResult:
        entities: list[Entity] = [{"text": span.text, "label": span.label} for span in self.spans]
        return {"entities": entities, "relations": list(self.relations)}


def _order_word(order: int | None) -> str:
    if order is None or order < 1:
        return "nhất"
    if order <= len(ORDER_WORDS):
        return ORDER_WORDS[order - 1]
    return str(order)


def _split_spouse_name(name: str) -> tuple[str, str | None]:
    parts = re.split(r"\s*\+\s*", name, maxsplit=1)
    if len(parts) == 2:
        left, right = parts[0].strip(), parts[1].strip()
        if left and right:
            return left, right
    return name.strip(), None


def _map_parent_relation(side: str) -> RelationType:
    return "MOTHER_OF" if side.lower() == "mid" else "FATHER_OF"


def _node_map(pha_he: dict[str, Any]) -> dict[int, dict[str, Any]]:
    mapping: dict[int, dict[str, Any]] = {}
    for node in pha_he.get("nodes", []):
        if isinstance(node, dict) and node.get("node_id") is not None:
            mapping[int(node["node_id"])] = node
    return mapping


def generate_synthetic_pha_ky(
    pha_he: dict[str, Any],
    *,
    lineage_name: str = "",
    max_nodes: int = 500,
) -> dict[str, Any]:
    """
    Build synthetic Quốc ngữ Phả ký and aligned gold extraction from ``pha_he``.

    Output is deterministic template prose — tag ``source=synthetic_from_pha_he``.
    """
    nodes = [node for node in pha_he.get("nodes", []) if isinstance(node, dict)]
    nodes = nodes[:max_nodes]
    by_id = _node_map(pha_he)

    builder = _Builder()
    title = lineage_name or str(pha_he.get("lineage_name") or "Gia phả")
    builder.add_plain("Phả ký (tổng hợp từ sơ đồ phả hệ): ")
    builder.add_labeled_span(title, "LOC")
    builder.blank_line()

    generations: dict[int, list[dict[str, Any]]] = {}
    for node in nodes:
        if node.get("is_spouse_row"):
            continue
        generation = int(node.get("generation") or 0)
        generations.setdefault(generation, []).append(node)

    emitted_names: set[str] = set()

    for generation in sorted(generations):
        gen_nodes = generations[generation]
        if generation > 0:
            builder.add_labeled_span(f"Đời thứ {generation}", "GENERATION")
            builder.add_plain(": ")
            builder.newline()

        for node in gen_nodes:
            raw_name = str(node.get("name") or "").strip()
            if not raw_name:
                continue
            primary, spouse = _split_spouse_name(raw_name)
            order = node.get("order_in_generation")

            if primary not in emitted_names:
                prefix = "Ông " if generation > 0 else ""
                if order is not None:
                    builder.add_labeled_span(f"Người con thứ {_order_word(int(order))}", "ORDER")
                    builder.add_plain(": ")
                builder.add_labeled_span(f"{prefix}{primary}".strip(), "PER_NAME")
                emitted_names.add(primary)
                builder.add_plain(". ")
                builder.newline()

            if spouse and spouse not in emitted_names:
                builder.add_labeled_span(f"{primary}", "PER_NAME")
                builder.add_plain(" lập gia thất với ")
                builder.add_labeled_span(f"bà {spouse}", "PER_NAME")
                builder.add_relation("SPOUSE", primary, f"bà {spouse}")
                emitted_names.add(spouse)
                builder.add_plain(". ")
                builder.newline()

    builder.blank_line()
    builder.add_plain("Quan hệ cha/mẹ — con: ")
    builder.newline()

    rel_count = 0
    for rel in pha_he.get("relationships", []):
        if not isinstance(rel, dict) or rel.get("type") != "parent_of":
            continue
        parent = by_id.get(int(rel.get("from_id", -1)))
        child = by_id.get(int(rel.get("to_id", -1)))
        if not parent or not child:
            continue
        parent_name = str(parent.get("name") or "").split("+")[0].strip()
        child_name = str(child.get("name") or "").split("+")[0].strip()
        if not parent_name or not child_name:
            continue

        rel_type = _map_parent_relation(str(rel.get("side") or "fid"))
        side_word = "Bà" if rel_type == "MOTHER_OF" else "Ông"
        builder.add_labeled_span(f"{side_word} {parent_name}", "PER_NAME")
        builder.add_plain(" hạ sinh ")
        builder.add_labeled_span(child_name, "PER_NAME")
        builder.add_plain(". ")
        builder.add_relation(rel_type, f"{side_word} {parent_name}", child_name)
        rel_count += 1
        builder.newline()
        if rel_count >= max_nodes:
            break

    text = builder.text()
    extraction = builder.extraction()
    return {
        "text": text,
        "extraction": extraction,
        "stats": {
            "char_count": len(text),
            "entity_count": len(extraction["entities"]),
            "relation_count": len(extraction["relations"]),
            "node_count": len(nodes),
            "relationship_count": rel_count,
        },
    }


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def export_synthetic_tree(
    *,
    tree_id: int,
    pha_he: dict[str, Any],
    meta: dict[str, Any],
    output_dir: Path,
    max_nodes: int,
) -> dict[str, Any]:
    lineage = str(meta.get("lineage_name") or pha_he.get("lineage_name") or f"tree_{tree_id}")
    generated = generate_synthetic_pha_ky(pha_he, lineage_name=lineage, max_nodes=max_nodes)
    text = generated["text"]
    extraction = generated["extraction"]

    out = output_dir / str(tree_id)
    out.mkdir(parents=True, exist_ok=True)

    (out / "synthetic_pha_ky.txt").write_text(text + "\n", encoding="utf-8")
    (out / "gold.entities.json").write_text(
        json.dumps(extraction, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )

    training = to_training_record(
        tree_id=tree_id,
        text=text,
        extraction=extraction,
        source_url=str(meta.get("pha_he_url") or pha_he.get("source_url") or ""),
        title=lineage,
    )
    training["source"] = "synthetic_from_pha_he"
    (out / "gold.training.json").write_text(
        json.dumps(training, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )

    ls_result = build_gold_ls_result(text, extraction, model_version="synthetic-pha-he-v1")
    annotation = {
        "result": ls_result,
        "ground_truth": True,
        "was_cancelled": False,
        "lead_time": 0.0,
    }
    (out / "gold.ls_annotation.json").write_text(
        json.dumps(annotation, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )

    metadata = {
        "tree_id": tree_id,
        "source": "synthetic_from_pha_he",
        "lineage_name": lineage,
        "generated_at": _now_iso(),
        "real_pha_ky_url": meta.get("pha_ky_url"),
        "pha_he_url": meta.get("pha_he_url") or pha_he.get("source_url"),
        **generated["stats"],
    }
    (out / "metadata.json").write_text(
        json.dumps(metadata, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return metadata


def select_synthetic_candidates_from_corpus(
    corpus_dir: Path,
    *,
    min_nodes: int = 20,
    max_relation_cues: int = 2,
    limit: int | None = None,
) -> list[int]:
    from label_studio_pipeline.corpus_store import load_json
    from label_studio_pipeline.pha_ky_assessment import PhaKyAssessmentConfig, assess_pha_ky

    cfg = PhaKyAssessmentConfig(require_diagram_overlap=False)
    candidates: list[tuple[int, int]] = []

    for tree_path in sorted(corpus_dir.iterdir(), key=lambda p: int(p.name) if p.name.isdigit() else 0):
        if not tree_path.is_dir() or not tree_path.name.isdigit():
            continue
        tree_id = int(tree_path.name)
        pk, ph = tree_path / "pha_ky.txt", tree_path / "pha_he.json"
        if not pk.is_file() or not ph.is_file():
            continue
        pha_he = load_json(ph) or {}
        nodes = int(pha_he.get("node_count") or 0)
        if nodes < min_nodes:
            continue
        text = pk.read_text(encoding="utf-8", errors="replace")
        meta = load_json(tree_path / "meta.json") or {}
        assessment = assess_pha_ky(text, tree_id=tree_id, pha_he=pha_he, meta=meta, config=cfg)
        cues = int(assessment.metrics.get("relation_cue_hits") or 0)
        if cues <= max_relation_cues:
            candidates.append((tree_id, nodes))

    candidates.sort(key=lambda item: -item[1])
    ids = [tree_id for tree_id, _ in candidates]
    if limit is not None:
        return ids[:limit]
    return ids
