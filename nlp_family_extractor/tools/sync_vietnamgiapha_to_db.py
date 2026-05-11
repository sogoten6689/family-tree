from __future__ import annotations

import argparse
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from sqlalchemy import create_engine, text


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _default_db_config() -> Dict[str, Any]:
    return {
        "host": os.getenv("MYSQL_HOST", "127.0.0.1"),
        "port": int(os.getenv("MYSQL_PORT", "3309")),
        "database": os.getenv("MYSQL_DATABASE", "family_tree"),
        "user": os.getenv("MYSQL_USER", "family_user"),
        "password": os.getenv("MYSQL_PASSWORD", "family_password"),
    }


def _db_url(cfg: Dict[str, Any]) -> str:
    return (
        f"mysql+pymysql://{cfg['user']}:{cfg['password']}@{cfg['host']}:{cfg['port']}/{cfg['database']}"
        "?charset=utf8mb4"
    )


def _ensure_schema(engine) -> None:
    ddl = """
    CREATE TABLE IF NOT EXISTS family_tree (
        id          VARCHAR(64)  NOT NULL PRIMARY KEY,
        name        VARCHAR(255) NOT NULL,
        description TEXT         NULL,
        nodes_json  JSON         NOT NULL,
        node_count  INT          NOT NULL DEFAULT 0,
        created_at  VARCHAR(64)  NOT NULL,
        updated_at  VARCHAR(64)  NOT NULL,
        created_ts  TIMESTAMP    DEFAULT CURRENT_TIMESTAMP,
        updated_ts  TIMESTAMP    DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
    """
    with engine.begin() as conn:
        conn.execute(text(ddl))


def _safe_text(value: Any, fallback: str) -> str:
    if isinstance(value, str):
        cleaned = value.strip()
        if cleaned:
            return cleaned
    return fallback


def _normalize_nodes(raw_nodes: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    inferred_parent_by_child = _infer_parent_by_child(raw_nodes)
    normalized: List[Dict[str, Any]] = []

    for node in raw_nodes:
        if not isinstance(node, dict):
            continue

        node_id = node.get("node_id")
        try:
            parsed_id = int(node_id)
        except (TypeError, ValueError):
            continue

        item: Dict[str, Any] = {
            "id": parsed_id,
            "name": _safe_text(node.get("name"), fallback=f"Node {parsed_id}"),
            "title": _safe_text(node.get("label"), fallback=f"Node {parsed_id}"),
        }

        gender = node.get("gender")
        if gender in ("male", "female"):
            item["gender"] = gender

        generation = node.get("generation")
        order = node.get("order_in_generation")
        if isinstance(generation, int) and isinstance(order, int):
            item["bio"] = f"Generation {generation}, order {order}"

        detail = node.get("detail")
        if isinstance(detail, dict):
            display_name = detail.get("display_name")
            if isinstance(display_name, str) and display_name.strip():
                # Keep name from detail page, strip trailing gender marker in parentheses.
                item["name"] = display_name.replace("(Nam)", "").replace("(Nữ)", "").strip()

            detail_birth = _as_int(detail.get("birth_year"))
            if detail_birth is not None:
                item["birthYear"] = detail_birth

            detail_death = _as_int(detail.get("death_year"))
            if detail_death is not None:
                item["deathYear"] = detail_death

            note = detail.get("note")
            if isinstance(note, str) and note.strip():
                item["bio"] = note.strip()

            detail_title = detail.get("common_name") or detail.get("courtesy_name")
            if isinstance(detail_title, str) and detail_title.strip():
                item["title"] = detail_title.strip()

            burial_place = detail.get("burial_place")
            if isinstance(burial_place, str) and burial_place.strip():
                item["burialPlace"] = burial_place.strip()

            children_ids = detail.get("children_node_ids")
            if isinstance(children_ids, list):
                item["childrenNodeIds"] = [x for x in children_ids if isinstance(x, int)]

            item["detail"] = detail

        parent_info = inferred_parent_by_child.get(parsed_id)
        if parent_info:
            if parent_info.get("side") == "mid":
                item["mid"] = int(parent_info["parent_id"])
            else:
                item["fid"] = int(parent_info["parent_id"])

        normalized.append(item)

    normalized.sort(key=lambda x: int(x["id"]))
    return normalized


def _infer_parent_by_child(raw_nodes: List[Dict[str, Any]]) -> Dict[int, Dict[str, Any]]:
    """Infer parent mapping from generation labels in traversal order.

    Child at generation g uses latest seen node at generation g-1.
    Parent side inferred from parent gender (female->mid, else fid).
    """
    latest_by_generation: Dict[int, Dict[str, Any]] = {}
    parent_by_child: Dict[int, Dict[str, Any]] = {}

    for node in raw_nodes:
        if not isinstance(node, dict):
            continue

        node_id = _as_int(node.get("node_id"))
        generation = _as_int(node.get("generation"))
        if node_id is None or generation is None:
            continue

        if generation > 1:
            parent = latest_by_generation.get(generation - 1)
            if parent is not None:
                parent_id = _as_int(parent.get("node_id"))
                if parent_id is not None:
                    parent_gender = parent.get("gender")
                    side = "mid" if parent_gender == "female" else "fid"
                    parent_by_child[node_id] = {
                        "parent_id": parent_id,
                        "side": side,
                    }

        latest_by_generation[generation] = node

    return parent_by_child


def _as_int(value: Any) -> Optional[int]:
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _build_tree_document(source_json: Dict[str, Any], source_file: Path) -> Tuple[str, Dict[str, Any]]:
    tree_id = int(source_json["tree_id"])
    store_id = f"vgp-{tree_id}"
    title = _safe_text(
        source_json.get("lineage_name"),
        fallback=_safe_text(source_json.get("title"), fallback=f"VietnamGiaPha tree {tree_id}"),
    )
    source_url = _safe_text(source_json.get("url"), fallback="")

    nodes = _normalize_nodes(source_json.get("nodes", []))
    now = _now_iso()

    doc: Dict[str, Any] = {
        "id": store_id,
        "name": title,
        "description": f"Synced from {source_url} | source={source_file.name}",
        "created_at": now,
        "updated_at": now,
        "nodes": nodes,
    }
    return store_id, doc


def _load_json(path: Path) -> Dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError("JSON root must be an object")
    if "tree_id" not in data:
        raise ValueError("Missing tree_id")
    return data


def sync(input_dir: Path, db_cfg: Dict[str, Any], dry_run: bool) -> Dict[str, Any]:
    files = sorted(input_dir.glob("*.json"))
    report: Dict[str, Any] = {
        "input_dir": str(input_dir),
        "total_files": len(files),
        "upserted": [],
        "errors": [],
    }

    if dry_run:
        for file in files:
            try:
                src = _load_json(file)
                store_id, doc = _build_tree_document(src, file)
                report["upserted"].append(
                    {
                        "store_id": store_id,
                        "tree_id": src.get("tree_id"),
                        "node_count": len(doc.get("nodes", [])),
                        "source": file.name,
                        "mode": "dry-run",
                    }
                )
            except Exception as exc:
                report["errors"].append({"file": file.name, "error": str(exc)})
        return report

    engine = create_engine(_db_url(db_cfg), pool_pre_ping=True, future=True)
    _ensure_schema(engine)

    stmt = text(
        """
        INSERT INTO family_tree (id, name, description, nodes_json, node_count, created_at, updated_at)
        VALUES (:id, :name, :description, CAST(:nodes_json AS JSON), :node_count, :created_at, :updated_at)
        ON DUPLICATE KEY UPDATE
            name = VALUES(name),
            description = VALUES(description),
            nodes_json = VALUES(nodes_json),
            node_count = VALUES(node_count),
            updated_at = VALUES(updated_at)
        """
    )

    with engine.begin() as conn:
        for file in files:
            try:
                src = _load_json(file)
                store_id, doc = _build_tree_document(src, file)

                conn.execute(
                    stmt,
                    {
                        "id": doc["id"],
                        "name": doc["name"],
                        "description": doc["description"],
                        "nodes_json": json.dumps(doc["nodes"], ensure_ascii=False),
                        "node_count": len(doc["nodes"]),
                        "created_at": doc["created_at"],
                        "updated_at": doc["updated_at"],
                    },
                )

                report["upserted"].append(
                    {
                        "store_id": store_id,
                        "tree_id": src.get("tree_id"),
                        "node_count": len(doc.get("nodes", [])),
                        "source": file.name,
                        "mode": "upsert",
                    }
                )
            except Exception as exc:
                report["errors"].append({"file": file.name, "error": str(exc)})

    return report


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Sync vietnamgiapha JSON files into MySQL family_tree table")
    parser.add_argument(
        "--input-dir",
        type=Path,
        default=Path("data/vietnamgiapha/json"),
        help="Directory that contains crawled JSON files",
    )
    parser.add_argument("--db-host", default=None, help="MySQL host")
    parser.add_argument("--db-port", type=int, default=None, help="MySQL port")
    parser.add_argument("--db-name", default=None, help="MySQL database")
    parser.add_argument("--db-user", default=None, help="MySQL username")
    parser.add_argument("--db-password", default=None, help="MySQL password")
    parser.add_argument("--dry-run", action="store_true", help="Validate and transform without writing DB")
    parser.add_argument(
        "--report",
        type=Path,
        default=Path("data/vietnamgiapha/sync-report.json"),
        help="Path to write sync report",
    )
    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()

    db_cfg = _default_db_config()
    if args.db_host:
        db_cfg["host"] = args.db_host
    if args.db_port:
        db_cfg["port"] = args.db_port
    if args.db_name:
        db_cfg["database"] = args.db_name
    if args.db_user:
        db_cfg["user"] = args.db_user
    if args.db_password:
        db_cfg["password"] = args.db_password

    report = sync(args.input_dir, db_cfg=db_cfg, dry_run=args.dry_run)
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    print(f"Input files: {report['total_files']}")
    print(f"Upserted: {len(report['upserted'])}")
    print(f"Errors: {len(report['errors'])}")
    print(f"Report: {args.report}")


if __name__ == "__main__":
    main()
