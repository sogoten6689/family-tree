from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple

CANONICAL_NODE_FIELDS = frozenset(
    {
        "id",
        "name",
        "gender",
        "birthYear",
        "deathYear",
        "fid",
        "mid",
        "pids",
        "title",
        "avatar",
        "bio",
    }
)

# VGP / provenance extensions — stored in family_tree_node_meta.meta_json (D1).
NODE_META_FIELDS = frozenset(
    {
        "detail",
        "burialPlace",
        "childrenNodeIds",
        "provenance",
    }
)


class BalkanNodeValidationError(ValueError):
    pass


def extract_node_meta(raw: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    if not isinstance(raw, dict):
        return None
    meta = {key: raw[key] for key in NODE_META_FIELDS if key in raw and raw[key] is not None}
    return meta or None


def build_canonical_node(
    payload: Dict[str, Any],
    *,
    node_id: Any,
    require_name_gender: bool = True,
) -> Dict[str, Any]:
    """Build a strict Balkan node — strips unknown fields (D5)."""
    if not isinstance(payload, dict):
        raise BalkanNodeValidationError("node payload must be object")

    try:
        parsed_id = int(node_id)
    except (TypeError, ValueError) as exc:
        raise BalkanNodeValidationError("node id must be integer") from exc
    if parsed_id <= 0:
        raise BalkanNodeValidationError("node id must be positive")

    name = payload.get("name")
    if require_name_gender and (not isinstance(name, str) or not name.strip()):
        raise BalkanNodeValidationError("node.name is required")

    gender = payload.get("gender")
    if require_name_gender and gender not in ("male", "female"):
        raise BalkanNodeValidationError("node.gender must be 'male' or 'female'")
    if gender is not None and gender not in ("male", "female"):
        raise BalkanNodeValidationError("node.gender must be 'male' or 'female'")

    node: Dict[str, Any] = {
        "id": parsed_id,
        "name": name.strip() if isinstance(name, str) else payload.get("name"),
    }
    if gender is not None:
        node["gender"] = gender

    if payload.get("birthYear") is not None:
        node["birthYear"] = int(payload["birthYear"])
    if payload.get("deathYear") is not None:
        node["deathYear"] = int(payload["deathYear"])

    for key in ("fid", "mid"):
        if payload.get(key) is not None:
            node[key] = int(payload[key])

    if payload.get("pids") is not None:
        pids = payload["pids"]
        if not isinstance(pids, list):
            raise BalkanNodeValidationError("node.pids must be array")
        deduped = sorted({int(pid) for pid in pids if pid is not None})
        if deduped:
            node["pids"] = deduped

    for key in ("title", "avatar", "bio"):
        if key in payload and payload[key] is not None:
            node[key] = payload[key]

    return node


def strip_nodes_and_collect_meta(
    nodes: List[Dict[str, Any]],
    *,
    require_name_gender: bool = True,
) -> Tuple[List[Dict[str, Any]], Dict[int, Dict[str, Any]]]:
    """Partition raw nodes into canonical nodes + per-node meta map (D1/D5)."""
    if not isinstance(nodes, list):
        raise BalkanNodeValidationError("nodes must be an array")

    meta_map: Dict[int, Dict[str, Any]] = {}
    normalized: List[Dict[str, Any]] = []

    for item in nodes:
        if not isinstance(item, dict):
            raise BalkanNodeValidationError("each node must be an object")
        raw_id = item.get("id", item.get("node_id"))
        meta = extract_node_meta(item)
        if meta is not None:
            try:
                meta_map[int(raw_id)] = meta
            except (TypeError, ValueError):
                pass
        normalized.append(
            build_canonical_node(item, node_id=raw_id, require_name_gender=require_name_gender)
        )

    ids = [int(node["id"]) for node in normalized]
    if len(set(ids)) != len(ids):
        raise BalkanNodeValidationError("duplicate node id detected")
    known_ids = set(ids)

    for node in normalized:
        for key in ("fid", "mid"):
            if key in node and node[key] not in known_ids:
                raise BalkanNodeValidationError(f"{key}={node[key]} does not reference existing node")
        if "pids" in node:
            for pid in node["pids"]:
                if pid not in known_ids:
                    raise BalkanNodeValidationError(f"pids contains unknown node id '{pid}'")
                if pid == node["id"]:
                    raise BalkanNodeValidationError("pids cannot reference self")

    return normalized, meta_map
