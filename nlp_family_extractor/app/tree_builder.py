from __future__ import annotations

from collections import defaultdict
from typing import Any, Dict, List, Set


def build_tree_architecture(data: Dict[str, Any]) -> Dict[str, Any]:
    people = data.get("people", [])
    relationships = data.get("relationships", [])

    nodes = {p["id"]: p for p in people if "id" in p}
    children_map: Dict[str, List[str]] = defaultdict(list)
    parent_count: Dict[str, int] = defaultdict(int)

    for rel in relationships:
        if rel.get("type") != "parent_of":
            continue
        parent_id = rel.get("from_id")
        child_id = rel.get("to_id")
        if parent_id not in nodes or child_id not in nodes:
            continue

        if child_id not in children_map[parent_id]:
            children_map[parent_id].append(child_id)
            parent_count[child_id] += 1

    roots = [pid for pid in nodes.keys() if parent_count.get(pid, 0) == 0]
    roots.sort()

    for pid in children_map:
        children_map[pid].sort()

    return {
        "roots": roots,
        "children_map": dict(children_map),
        "nodes": nodes,
    }


def build_nested_tree(tree_arch: Dict[str, Any]) -> List[Dict[str, Any]]:
    nodes: Dict[str, Dict[str, Any]] = tree_arch.get("nodes", {})
    children_map: Dict[str, List[str]] = tree_arch.get("children_map", {})
    roots: List[str] = tree_arch.get("roots", [])

    def walk(node_id: str, visiting: Set[str]) -> Dict[str, Any]:
        node = nodes.get(node_id, {"id": node_id, "full_name": node_id})
        if node_id in visiting:
            return {
                "id": node_id,
                "full_name": node.get("full_name", node_id),
                "cycle": True,
                "children": [],
            }

        next_visiting = set(visiting)
        next_visiting.add(node_id)

        return {
            "id": node_id,
            "full_name": node.get("full_name"),
            "birth_year": node.get("birth_year"),
            "death_year": node.get("death_year"),
            "gender": node.get("gender"),
            "children": [walk(cid, next_visiting) for cid in children_map.get(node_id, [])],
        }

    return [walk(rid, set()) for rid in roots]
