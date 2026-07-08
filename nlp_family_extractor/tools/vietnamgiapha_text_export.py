from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _safe_text(value: Any) -> str:
    if isinstance(value, str):
        return value.strip()
    return ""


def _hashable_node(node: Dict[str, Any]) -> Dict[str, Any]:
    detail = node.get("detail")
    detail_payload: Dict[str, Any] = {}
    if isinstance(detail, dict):
        for key in (
            "note",
            "display_name",
            "birth_year",
            "death_year",
            "parent_text",
            "siblings_text",
            "birth_text",
            "death_text",
            "burial_place",
            "common_name",
            "courtesy_name",
        ):
            value = detail.get(key)
            if value not in (None, ""):
                detail_payload[key] = value

    return {
        "node_id": node.get("node_id"),
        "name": node.get("name"),
        "label": node.get("label"),
        "gender": node.get("gender"),
        "generation": node.get("generation"),
        "order_in_generation": node.get("order_in_generation"),
        "detail": detail_payload,
    }


def compute_content_hash(page_data: Dict[str, Any]) -> str:
    """SHA256 of node_count, relationships, and sorted node identity/detail text."""
    payload = {
        "node_count": page_data.get("node_count"),
        "relationships": page_data.get("relationships", []),
        "nodes": sorted(
            [_hashable_node(item) for item in page_data.get("nodes", []) if isinstance(item, dict)],
            key=lambda item: int(item.get("node_id") or 0),
        ),
    }
    encoded = json.dumps(payload, ensure_ascii=False, sort_keys=True).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def compute_nodes_hash(nodes: List[Dict[str, Any]]) -> str:
    encoded = json.dumps(nodes, ensure_ascii=False, sort_keys=True).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def build_tree_text(tree_json: Dict[str, Any]) -> str:
    """Ghép lineage_name + từng node.detail → plain text UTF-8."""
    parts: List[str] = []

    lineage = _safe_text(tree_json.get("lineage_name"))
    title = _safe_text(tree_json.get("title"))
    if lineage:
        parts.append(f"Dòng họ: {lineage}")
    if title and title != lineage:
        parts.append(f"Tiêu đề: {title}")

    source_url = _safe_text(tree_json.get("url"))
    if source_url:
        parts.append(f"Nguồn: {source_url}")

    parts.append("")
    parts.append("=== Thành viên ===")

    nodes = tree_json.get("nodes", [])
    if not isinstance(nodes, list):
        nodes = []

    sorted_nodes = sorted(
        [item for item in nodes if isinstance(item, dict)],
        key=lambda item: (
            int(item.get("generation") or 0),
            int(item.get("order_in_generation") or 0),
            int(item.get("node_id") or 0),
        ),
    )

    for node in sorted_nodes:
        node_id = node.get("node_id")
        name = _safe_text(node.get("name")) or _safe_text(node.get("label")) or f"Node {node_id}"
        generation = node.get("generation")
        order = node.get("order_in_generation")
        header_bits = [name]
        if isinstance(generation, int):
            if isinstance(order, int):
                header_bits.append(f"đời {generation}, thứ {order}")
            else:
                header_bits.append(f"đời {generation}")

        parts.append("")
        parts.append(" — ".join(header_bits))

        detail = node.get("detail")
        if isinstance(detail, dict):
            display_name = _safe_text(detail.get("display_name"))
            if display_name and display_name != name:
                parts.append(f"Tên hiển thị: {display_name}")

            for label, key in (
                ("Tên thường gọi", "common_name"),
                ("Tên tự", "courtesy_name"),
                ("Sinh", "birth_text"),
                ("Mất", "death_text"),
                ("An táng", "burial_place"),
                ("Cha/mẹ", "parent_text"),
                ("Anh chị em", "siblings_text"),
                ("Ghi chú", "note"),
            ):
                text = _safe_text(detail.get(key))
                if text:
                    parts.append(f"{label}: {text}")

            birth_year = detail.get("birth_year")
            death_year = detail.get("death_year")
            if isinstance(birth_year, int):
                parts.append(f"Năm sinh: {birth_year}")
            if isinstance(death_year, int):
                parts.append(f"Năm mất: {death_year}")
        else:
            bio = _safe_text(node.get("bio"))
            if bio:
                parts.append(bio)

    return "\n".join(parts).strip() + "\n"


def build_members_index(tree_json: Dict[str, Any]) -> str:
    lines: List[str] = []
    nodes = tree_json.get("nodes", [])
    if not isinstance(nodes, list):
        return ""

    sorted_nodes = sorted(
        [item for item in nodes if isinstance(item, dict)],
        key=lambda item: (
            int(item.get("generation") or 0),
            int(item.get("order_in_generation") or 0),
            int(item.get("node_id") or 0),
        ),
    )

    for node in sorted_nodes:
        node_id = node.get("node_id")
        name = _safe_text(node.get("name")) or _safe_text(node.get("label")) or f"Node {node_id}"
        generation = node.get("generation")
        order = node.get("order_in_generation")
        prefix = ""
        if isinstance(generation, int) and isinstance(order, int):
            prefix = f"{generation}.{order} "
        elif isinstance(generation, int):
            prefix = f"{generation}. "

        detail = node.get("detail") if isinstance(node.get("detail"), dict) else {}
        birth = detail.get("birth_year") or node.get("birthYear")
        death = detail.get("death_year") or node.get("deathYear")
        note = _safe_text(detail.get("note")) or _safe_text(node.get("bio"))

        birth_text = str(birth) if isinstance(birth, int) else "-"
        death_text = str(death) if isinstance(death, int) else "-"
        note_text = note or "-"
        lines.append(f"{prefix}{name} | sinh {birth_text} | mất {death_text} | {note_text}")

    return "\n".join(lines) + ("\n" if lines else "")


def export_tree_text_files(
    tree_json: Dict[str, Any],
    *,
    output_root: Path,
    force: bool = False,
) -> Tuple[bool, Optional[Path]]:
    tree_id = int(tree_json["tree_id"])
    text_dir = output_root / "text" / str(tree_id)
    full_text_path = text_dir / "full_text.txt"
    members_path = text_dir / "members_index.txt"
    meta_path = text_dir / "meta.json"

    if not force and full_text_path.exists() and members_path.exists() and meta_path.exists():
        return False, text_dir

    text_dir.mkdir(parents=True, exist_ok=True)
    full_text = build_tree_text(tree_json)
    members_index = build_members_index(tree_json)

    full_text_path.write_text(full_text, encoding="utf-8")
    members_path.write_text(members_index, encoding="utf-8")

    meta = {
        "tree_id": tree_id,
        "lineage_name": tree_json.get("lineage_name"),
        "url": tree_json.get("url"),
        "content_hash": tree_json.get("content_hash") or compute_content_hash(tree_json),
        "exported_at": _now_iso(),
        "char_count": len(full_text),
        "member_count": tree_json.get("node_count", 0),
    }
    meta_path.write_text(json.dumps(meta, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return True, text_dir


def export_text_for_json_file(json_path: Path, *, output_root: Path, force: bool = False) -> Dict[str, Any]:
    tree_json = json.loads(json_path.read_text(encoding="utf-8"))
    if not isinstance(tree_json, dict):
        raise ValueError("JSON root must be an object")
    if "content_hash" not in tree_json:
        tree_json["content_hash"] = compute_content_hash(tree_json)

    built, text_dir = export_tree_text_files(tree_json, output_root=output_root, force=force)
    return {
        "tree_id": tree_json.get("tree_id"),
        "source": json_path.name,
        "built": built,
        "text_dir": str(text_dir) if text_dir else None,
    }
