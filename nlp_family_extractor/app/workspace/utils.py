from __future__ import annotations

from typing import Any, Dict, List


def compute_generation_count(nodes: List[Dict[str, Any]]) -> int:
    if not nodes:
        return 0

    child_ids: set[int] = set()
    children_map: Dict[int, List[int]] = {}

    for node in nodes:
        try:
            node_id = int(node["id"])
        except (KeyError, TypeError, ValueError):
            continue
        for key in ("fid", "mid"):
            parent_raw = node.get(key)
            if parent_raw is None:
                continue
            try:
                parent_id = int(parent_raw)
            except (TypeError, ValueError):
                continue
            child_ids.add(node_id)
            children_map.setdefault(parent_id, []).append(node_id)

    roots = []
    for node in nodes:
        try:
            node_id = int(node["id"])
        except (KeyError, TypeError, ValueError):
            continue
        if node_id not in child_ids:
            roots.append(node_id)

    if not roots:
        return 1

    max_generation = 1
    queue = [(root_id, 1) for root_id in roots]
    visited: Dict[int, int] = {root_id: 1 for root_id in roots}

    while queue:
        current_id, generation = queue.pop(0)
        max_generation = max(max_generation, generation)
        for child_id in children_map.get(current_id, []):
            next_generation = generation + 1
            if child_id not in visited or next_generation > visited[child_id]:
                visited[child_id] = next_generation
                queue.append((child_id, next_generation))

    return max_generation


def enrich_tree_summary(summary: Dict[str, Any], *, nodes: List[Dict[str, Any]] | None = None) -> Dict[str, Any]:
    enriched = dict(summary)
    node_list = nodes if nodes is not None else []
    enriched["generation_count"] = compute_generation_count(node_list)
    enriched["is_public"] = bool(enriched.get("is_public", False))
    return enriched
