#!/usr/bin/env python3
"""Migrate legacy nodes_json: strip VGP extensions into family_tree_node_meta (D1/D5)."""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Any, Dict, List

from sqlalchemy import create_engine, text

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.balkan_node import strip_nodes_and_collect_meta
from app.node_meta.repository import NodeMetaRepository


def _db_url() -> str:
    host = os.getenv("MYSQL_HOST", "127.0.0.1")
    port = os.getenv("MYSQL_PORT", "3306")
    database = os.getenv("MYSQL_DATABASE", "family_tree")
    user = os.getenv("MYSQL_USER", "family_user")
    password = os.getenv("MYSQL_PASSWORD", "family_password")
    return (
        f"mysql+pymysql://{user}:{password}@{host}:{port}/{database}?charset=utf8mb4"
    )


def _load_nodes(raw: Any) -> List[Dict[str, Any]]:
    if isinstance(raw, str):
        parsed = json.loads(raw)
    else:
        parsed = raw
    if not isinstance(parsed, list):
        return []
    return [item for item in parsed if isinstance(item, dict)]


def migrate(*, dry_run: bool = False, tree_id: str | None = None) -> Dict[str, Any]:
    engine = create_engine(_db_url(), pool_pre_ping=True, future=True)
    meta_repo = NodeMetaRepository(engine)

    where = "WHERE id = :tree_id" if tree_id else ""
    params = {"tree_id": tree_id} if tree_id else {}

    report: Dict[str, Any] = {
        "dry_run": dry_run,
        "trees_processed": 0,
        "trees_updated": 0,
        "meta_rows_written": 0,
        "details": [],
    }

    with engine.connect() as conn:
        rows = conn.execute(
            text(f"SELECT id, nodes_json FROM family_tree {where} ORDER BY id"),
            params,
        ).mappings().all()

    for row in rows:
        tid = str(row["id"])
        raw_nodes = _load_nodes(row["nodes_json"])
        report["trees_processed"] += 1

        has_extensions = any(
            key in node
            for node in raw_nodes
            for key in ("detail", "burialPlace", "childrenNodeIds", "provenance")
        )
        if not has_extensions:
            report["details"].append({"tree_id": tid, "status": "skipped", "reason": "already_clean"})
            continue

        try:
            stripped, meta_map = strip_nodes_and_collect_meta(raw_nodes, require_name_gender=False)
        except Exception as exc:
            report["details"].append({"tree_id": tid, "status": "error", "error": str(exc)})
            continue

        detail = {
            "tree_id": tid,
            "status": "updated",
            "node_count": len(stripped),
            "meta_count": len(meta_map),
        }
        report["details"].append(detail)

        if dry_run:
            report["trees_updated"] += 1
            report["meta_rows_written"] += len(meta_map)
            continue

        nodes_json = json.dumps(stripped, ensure_ascii=False)
        with engine.begin() as conn:
            conn.execute(
                text(
                    "UPDATE family_tree "
                    "SET nodes_json = CAST(:nodes_json AS JSON), node_count = :node_count "
                    "WHERE id = :id"
                ),
                {"id": tid, "nodes_json": nodes_json, "node_count": len(stripped)},
            )
        if meta_map:
            meta_repo.upsert_many(tid, meta_map)
        report["trees_updated"] += 1
        report["meta_rows_written"] += len(meta_map)

    return report


def main() -> None:
    parser = argparse.ArgumentParser(description="Strip VGP node extensions into family_tree_node_meta")
    parser.add_argument("--dry-run", action="store_true", help="Report only, do not write")
    parser.add_argument("--tree-id", default=None, help="Migrate a single tree id")
    parser.add_argument(
        "--report",
        type=Path,
        default=Path("data/migrate_strip_node_extensions_report.json"),
    )
    args = parser.parse_args()

    report = migrate(dry_run=args.dry_run, tree_id=args.tree_id)
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    print(f"Trees processed: {report['trees_processed']}")
    print(f"Trees updated: {report['trees_updated']}")
    print(f"Meta rows written: {report['meta_rows_written']}")
    print(f"Report: {args.report}")


if __name__ == "__main__":
    main()
