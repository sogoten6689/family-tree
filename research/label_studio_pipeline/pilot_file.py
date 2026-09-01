"""Load tree_id lists from pilot / stratified JSON files."""

from __future__ import annotations

from pathlib import Path

from label_studio_pipeline.corpus_store import load_json, load_pilot_trees


def resolve_tree_ids(
    *,
    corpus_dir: Path,
    pilot_file: Path | None = None,
    tree_ids: list[int] | None = None,
) -> list[int]:
    if tree_ids:
        return tree_ids

    pilot_path = pilot_file or (corpus_dir / "pilot_trees.json")
    data = load_json(pilot_path) if pilot_path.is_file() else None
    if data:
        tree_ids_block = data.get("tree_ids")
        if isinstance(tree_ids_block, dict):
            all_ids = tree_ids_block.get("all")
            if isinstance(all_ids, list):
                return [int(x) for x in all_ids]
        selected = data.get("selected_tree_ids")
        if isinstance(selected, list):
            return [int(x) for x in selected]

    return load_pilot_trees(corpus_dir)
