"""Generate synthetic / hybrid Phả ký prose + gold labels from pha_he diagrams."""

from __future__ import annotations

import json
import re
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Literal

from label_studio_pipeline.cross_check import normalize_person_name
from label_studio_pipeline.gemini_extractor import Entity, ExtractionResult, Relation
from label_studio_pipeline.gold_builder import build_gold_ls_result, to_training_record
from label_studio_pipeline.pha_ky_assessment import _diagram_overlap

RelationType = Literal["FATHER_OF", "MOTHER_OF", "SPOUSE"]
GenerationMode = Literal["full", "supplement", "auto"]
Gender = Literal["male", "female", "unknown"]

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

HONORIFIC_PREFIXES = ("Ông cố", "Bà cố", "Ông", "Bà", "Cụ")

HYBRID_MARKER = "\n\n---\n(Bổ sung từ sơ đồ — chưa có trong phả ký thật)\n\n"

PARENT_CHILD_TEMPLATES = (
    "{parent} hạ sinh {child}.",
    "{child} là con của {parent}.",
    "{parent} sinh được {child}.",
)

SPOUSE_TEMPLATES_FEMALE = (
    "{a} lấy {b} làm vợ.",
    "{a} hôn phối với {b}.",
)

SPOUSE_TEMPLATES_MALE = (
    "{a} lấy {b} làm chồng.",
    "{a} hôn phối với {b}.",
)

CHILDREN_INTRO_TEMPLATES = (
    "{parent} có {count} người con: {children}.",
    "{parent} sinh được {count} người con, gồm: {children}.",
)


@dataclass
class ParsedPerson:
    raw: str
    bare: str
    core: str
    honorific: str
    gender: Gender
    display: str


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


def _strip_honorific(text: str) -> tuple[str, str]:
    cleaned = text.strip()
    for prefix in HONORIFIC_PREFIXES:
        if cleaned.lower().startswith(prefix.lower()):
            return prefix, cleaned[len(prefix) :].strip()
    return "", cleaned


def _infer_gender(bare: str, honorific: str) -> Gender:
    if honorific.lower().startswith("bà"):
        return "female"
    if honorific.lower().startswith("ông") or honorific.lower().startswith("cụ"):
        return "male"
    if re.search(r"\bThị\b", bare):
        return "female"
    if re.search(r"\bVăn\b", bare):
        return "male"
    return "unknown"


def _display_honorific(gender: Gender, honorific: str) -> str:
    if honorific:
        return honorific
    if gender == "female":
        return "Bà"
    if gender == "male":
        return "Ông"
    return ""


def parse_person(raw: str) -> ParsedPerson:
    cleaned = raw.strip()
    honorific, bare = _strip_honorific(cleaned)
    gender = _infer_gender(bare, honorific)
    prefix = _display_honorific(gender, honorific)
    display = f"{prefix} {bare}".strip() if prefix else bare
    core = normalize_person_name(bare) or bare.lower().strip()
    return ParsedPerson(
        raw=cleaned,
        bare=bare,
        core=core,
        honorific=prefix,
        gender=gender,
        display=display,
    )


def parse_couple(raw: str) -> tuple[ParsedPerson, ParsedPerson | None]:
    parts = re.split(r"\s*\+\s*", raw, maxsplit=1)
    primary = parse_person(parts[0])
    if len(parts) == 2 and parts[1].strip():
        return primary, parse_person(parts[1])
    return primary, None


def _name_in_prose(core: str, prose: str) -> bool:
    if len(core) < 2:
        return True
    lowered = prose.lower()
    if core.lower() in lowered:
        return True
    tokens = [token for token in core.split() if len(token) >= 2]
    if len(tokens) >= 2:
        return tokens[-1].lower() in lowered and tokens[-2].lower() in lowered
    return False


def _pick_template(key: str, templates: tuple[str, ...]) -> str:
    return templates[abs(hash(key)) % len(templates)]


def _node_map(pha_he: dict[str, Any]) -> dict[int, dict[str, Any]]:
    mapping: dict[int, dict[str, Any]] = {}
    for node in pha_he.get("nodes", []):
        if isinstance(node, dict) and node.get("node_id") is not None:
            mapping[int(node["node_id"])] = node
    return mapping


def _parent_children_map(pha_he: dict[str, Any]) -> dict[int, list[int]]:
    children: dict[int, list[int]] = defaultdict(list)
    for rel in pha_he.get("relationships", []):
        if not isinstance(rel, dict) or rel.get("type") != "parent_of":
            continue
        parent_id = int(rel.get("from_id", -1))
        child_id = int(rel.get("to_id", -1))
        if parent_id >= 0 and child_id >= 0:
            children[parent_id].append(child_id)
    for parent_id, child_ids in children.items():
        by_id = _node_map(pha_he)
        child_ids.sort(
            key=lambda cid: int(by_id.get(cid, {}).get("order_in_generation") or cid),
        )
    return children


def _child_parent_map(pha_he: dict[str, Any]) -> dict[int, tuple[int, str]]:
    mapping: dict[int, tuple[int, str]] = {}
    for rel in pha_he.get("relationships", []):
        if not isinstance(rel, dict) or rel.get("type") != "parent_of":
            continue
        child_id = int(rel.get("to_id", -1))
        parent_id = int(rel.get("from_id", -1))
        if child_id >= 0 and parent_id >= 0:
            mapping[child_id] = (parent_id, str(rel.get("side") or "fid"))
    return mapping


def choose_generation_mode(real_prose: str, pha_he: dict[str, Any]) -> GenerationMode:
    prose = real_prose.strip()
    overlap = _diagram_overlap(prose, pha_he)
    ratio = float(overlap.get("overlap_ratio") or 0)
    if len(prose) < 200:
        return "full"
    if ratio >= 0.45:
        return "supplement"
    return "full"


def _should_include_person(
    person: ParsedPerson,
    prose: str,
    mode: GenerationMode,
) -> bool:
    if mode == "supplement":
        return not _name_in_prose(person.core, prose)
    if len(prose.strip()) < 200:
        return True
    return not _name_in_prose(person.core, prose)


def _emit_parent_child(
    builder: _Builder,
    *,
    parent: ParsedPerson,
    child: ParsedPerson,
    rel_side: str,
) -> None:
    rel_type: RelationType = "MOTHER_OF" if rel_side.lower() == "mid" else "FATHER_OF"
    if rel_type == "MOTHER_OF" and parent.gender != "female":
        parent_display = parent.display if parent.honorific else f"Bà {parent.bare}"
    else:
        parent_display = parent.display
    template = _pick_template(f"{parent.core}->{child.core}", PARENT_CHILD_TEMPLATES)
    variant = PARENT_CHILD_TEMPLATES.index(template)
    if variant == 0:
        builder.add_labeled_span(parent_display, "PER_NAME")
        builder.add_plain(" hạ sinh ")
        builder.add_labeled_span(child.display, "PER_NAME")
        builder.add_plain(".")
    elif variant == 1:
        builder.add_labeled_span(child.display, "PER_NAME")
        builder.add_plain(" là con của ")
        builder.add_labeled_span(parent_display, "PER_NAME")
        builder.add_plain(".")
    else:
        builder.add_labeled_span(parent_display, "PER_NAME")
        builder.add_plain(" sinh được ")
        builder.add_labeled_span(child.display, "PER_NAME")
        builder.add_plain(".")
    builder.add_relation(rel_type, parent_display, child.display)
    builder.newline()


def _emit_spouse(
    builder: _Builder,
    *,
    left: ParsedPerson,
    right: ParsedPerson,
) -> None:
    if right.gender == "male" or (right.gender == "unknown" and left.gender == "female"):
        builder.add_labeled_span(left.display, "PER_NAME")
        builder.add_plain(" lấy ")
        builder.add_labeled_span(right.display, "PER_NAME")
        builder.add_plain(" làm chồng.")
    else:
        builder.add_labeled_span(left.display, "PER_NAME")
        builder.add_plain(" lấy ")
        builder.add_labeled_span(right.display, "PER_NAME")
        builder.add_plain(" làm vợ.")
    builder.add_relation("SPOUSE", left.display, right.display)
    builder.newline()


def generate_supplement_v2(
    pha_he: dict[str, Any],
    *,
    real_prose: str = "",
    lineage_name: str = "",
    mode: GenerationMode = "auto",
    max_sentences: int = 80,
) -> dict[str, Any]:
    """Template v2 — branch-oriented supplement from pha_he (A), gated by prose overlap (B)."""
    by_id = _node_map(pha_he)
    nodes = [node for node in pha_he.get("nodes", []) if isinstance(node, dict) and not node.get("is_spouse_row")]
    if not nodes:
        return {
            "text": "",
            "extraction": {"entities": [], "relations": []},
            "stats": {
                "char_count": 0,
                "entity_count": 0,
                "relation_count": 0,
                "sentence_count": 0,
                "missing_name_count": 0,
                "generation_mode": mode,
            },
        }

    prose = real_prose.strip()
    resolved_mode = choose_generation_mode(prose, pha_he) if mode == "auto" else mode
    children_map = _parent_children_map(pha_he)
    child_parent = _child_parent_map(pha_he)

    builder = _Builder()
    title = lineage_name or str(pha_he.get("lineage_name") or "Gia phả")
    if not prose:
        builder.add_plain("Phả ký (bổ sung từ sơ đồ phả hệ): ")
        builder.add_labeled_span(title, "LOC")
        builder.blank_line()

    sentence_count = 0
    missing_names = 0
    emitted_pairs: set[tuple[str, str]] = set()

    def emit_family_block(parent_id: int) -> None:
        nonlocal sentence_count, missing_names
        if sentence_count >= max_sentences:
            return
        parent_node = by_id.get(parent_id)
        if not parent_node:
            return
        parent_primary, parent_spouse = parse_couple(str(parent_node.get("name") or ""))
        child_ids = children_map.get(parent_id, [])
        child_people: list[ParsedPerson] = []
        for child_id in child_ids:
            if sentence_count >= max_sentences:
                break
            child_node = by_id.get(child_id)
            if not child_node:
                continue
            child_primary, _ = parse_couple(str(child_node.get("name") or ""))
            child_people.append(child_primary)

        needs_parent = _should_include_person(parent_primary, prose, resolved_mode)
        needs_children = [child for child in child_people if _should_include_person(child, prose, resolved_mode)]
        needs_spouse = parent_spouse is not None and _should_include_person(parent_spouse, prose, resolved_mode)

        if not needs_parent and not needs_children and not needs_spouse:
            return

        if child_people and needs_children:
            listed = ", ".join(child.display for child in child_people)
            template = _pick_template(parent_primary.core, CHILDREN_INTRO_TEMPLATES)
            sentence = template.format(parent=parent_primary.display, count=len(child_people), children=listed)
            builder.add_labeled_span(parent_primary.display, "PER_NAME")
            builder.add_plain(sentence[len(parent_primary.display) :])
            builder.newline()
            sentence_count += 1

        if parent_spouse and needs_spouse:
            _emit_spouse(builder, left=parent_primary, right=parent_spouse)
            sentence_count += 1
            missing_names += 1

        for child_id in child_ids:
            if sentence_count >= max_sentences:
                break
            child_node = by_id.get(child_id)
            if not child_node:
                continue
            child_primary, _ = parse_couple(str(child_node.get("name") or ""))
            if not _should_include_person(child_primary, prose, resolved_mode):
                continue
            pair_key = (parent_primary.core, child_primary.core)
            if pair_key in emitted_pairs:
                continue
            _, side = child_parent.get(child_id, (parent_id, "fid"))
            parent_for_rel = parent_primary
            if side.lower() == "mid" and parent_spouse is not None:
                parent_for_rel = parent_spouse
            _emit_parent_child(builder, parent=parent_for_rel, child=child_primary, rel_side=side)
            emitted_pairs.add(pair_key)
            sentence_count += 1
            missing_names += 1

    # Walk parents that have children in diagram order.
    parent_ids = sorted(
        children_map.keys(),
        key=lambda pid: (
            int(by_id.get(pid, {}).get("generation") or 0),
            int(by_id.get(pid, {}).get("order_in_generation") or pid),
        ),
    )
    for parent_id in parent_ids:
        emit_family_block(parent_id)

    # Root couples without emitted parent-child block (solo nodes).
    covered = set(children_map.keys()) | {cid for ids in children_map.values() for cid in ids}
    for node in sorted(nodes, key=lambda n: (int(n.get("generation") or 0), int(n.get("order_in_generation") or 0))):
        if sentence_count >= max_sentences:
            break
        node_id = int(node.get("node_id") or -1)
        if node_id in covered:
            continue
        primary, spouse = parse_couple(str(node.get("name") or ""))
        if not _should_include_person(primary, prose, resolved_mode):
            continue
        generation = int(node.get("generation") or 0)
        if generation > 0:
            builder.add_labeled_span(f"Đời thứ {generation}", "GENERATION")
            builder.add_plain(": ")
            builder.newline()
        builder.add_labeled_span(primary.display, "PER_NAME")
        builder.add_plain(". ")
        builder.newline()
        sentence_count += 1
        missing_names += 1
        if spouse and _should_include_person(spouse, prose, resolved_mode):
            _emit_spouse(builder, left=primary, right=spouse)
            sentence_count += 1

    text = builder.text().strip()
    extraction = builder.extraction()
    return {
        "text": text,
        "extraction": extraction,
        "stats": {
            "char_count": len(text),
            "entity_count": len(extraction["entities"]),
            "relation_count": len(extraction["relations"]),
            "sentence_count": sentence_count,
            "missing_name_count": missing_names,
            "generation_mode": resolved_mode,
            "diagram_overlap_ratio": _diagram_overlap(prose, pha_he).get("overlap_ratio"),
        },
    }


def build_hybrid_pha_ky(real_prose: str, supplement: str) -> str:
    real = real_prose.strip()
    extra = supplement.strip()
    if not extra:
        return real
    if not real:
        return extra
    return real + HYBRID_MARKER + extra


def generate_synthetic_pha_ky(
    pha_he: dict[str, Any],
    *,
    lineage_name: str = "",
    max_nodes: int = 500,
    real_prose: str = "",
    mode: GenerationMode = "auto",
) -> dict[str, Any]:
    """Backward-compatible entry — returns supplement bundle (v2 hybrid)."""
    _ = max_nodes
    generated = generate_supplement_v2(
        pha_he,
        real_prose=real_prose,
        lineage_name=lineage_name,
        mode=mode,
        max_sentences=80,
    )
    hybrid = build_hybrid_pha_ky(real_prose, generated["text"])
    return {
        **generated,
        "supplement_text": generated["text"],
        "hybrid_text": hybrid,
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
    real_pha_ky_text: str = "",
) -> dict[str, Any]:
    lineage = str(meta.get("lineage_name") or pha_he.get("lineage_name") or f"tree_{tree_id}")
    generated = generate_synthetic_pha_ky(
        pha_he,
        lineage_name=lineage,
        max_nodes=max_nodes,
        real_prose=real_pha_ky_text,
    )
    supplement = generated["supplement_text"]
    hybrid = generated["hybrid_text"]
    extraction = generated["extraction"]

    out = output_dir / str(tree_id)
    out.mkdir(parents=True, exist_ok=True)

    (out / "pha_ky_supplement.txt").write_text(supplement + ("\n" if supplement else ""), encoding="utf-8")
    (out / "pha_ky_hybrid.txt").write_text(hybrid + ("\n" if hybrid else ""), encoding="utf-8")
    (out / "synthetic_pha_ky.txt").write_text(supplement + ("\n" if supplement else ""), encoding="utf-8")

    if extraction["entities"] or extraction["relations"]:
        (out / "gold.entities.json").write_text(
            json.dumps(extraction, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        training = to_training_record(
            tree_id=tree_id,
            text=supplement,
            extraction=extraction,
            source_url=str(meta.get("pha_he_url") or pha_he.get("source_url") or ""),
            title=lineage,
        )
        training["source"] = "synthetic_supplement_v2"
        (out / "gold.training.json").write_text(
            json.dumps(training, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        ls_result = build_gold_ls_result(supplement, extraction, model_version="synthetic-pha-he-v2")
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
        "source": "synthetic_supplement_v2",
        "lineage_name": lineage,
        "generated_at": _now_iso(),
        "real_pha_ky_url": meta.get("pha_ky_url"),
        "pha_he_url": meta.get("pha_he_url") or pha_he.get("source_url"),
        "real_pha_ky_char_count": len(real_pha_ky_text),
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
