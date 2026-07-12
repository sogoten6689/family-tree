from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from sqlalchemy import text
from sqlalchemy.engine import Engine


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


class NodeMetaRepository:
    """Persist VGP detail and other node extensions in family_tree_node_meta (D1)."""

    def __init__(self, engine: Engine) -> None:
        self._engine = engine
        self.ensure_schema()

    def ensure_schema(self) -> None:
        ddl = """
        CREATE TABLE IF NOT EXISTS family_tree_node_meta (
            id              BIGINT       NOT NULL AUTO_INCREMENT PRIMARY KEY,
            family_tree_id  VARCHAR(64)  NOT NULL,
            node_id         INT          NOT NULL,
            meta_json       JSON         NOT NULL,
            created_at      VARCHAR(64)  NOT NULL,
            updated_at      VARCHAR(64)  NOT NULL,
            UNIQUE KEY uq_tree_node (family_tree_id, node_id),
            KEY idx_tree (family_tree_id)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
        """
        with self._engine.begin() as conn:
            conn.execute(text(ddl))

    def upsert_many(
        self,
        family_tree_id: str,
        meta_by_node_id: Dict[int, Dict[str, Any]],
    ) -> int:
        if not meta_by_node_id:
            return 0
        now = _now_iso()
        count = 0
        stmt = text(
            """
            INSERT INTO family_tree_node_meta
                (family_tree_id, node_id, meta_json, created_at, updated_at)
            VALUES
                (:family_tree_id, :node_id, CAST(:meta_json AS JSON), :created_at, :updated_at)
            ON DUPLICATE KEY UPDATE
                meta_json = VALUES(meta_json),
                updated_at = VALUES(updated_at)
            """
        )
        with self._engine.begin() as conn:
            for node_id, meta in meta_by_node_id.items():
                conn.execute(
                    stmt,
                    {
                        "family_tree_id": family_tree_id,
                        "node_id": int(node_id),
                        "meta_json": json.dumps(meta, ensure_ascii=False),
                        "created_at": now,
                        "updated_at": now,
                    },
                )
                count += 1
        return count

    def get(self, family_tree_id: str, node_id: int) -> Optional[Dict[str, Any]]:
        with self._engine.connect() as conn:
            row = conn.execute(
                text(
                    "SELECT meta_json FROM family_tree_node_meta "
                    "WHERE family_tree_id = :tree_id AND node_id = :node_id"
                ),
                {"tree_id": family_tree_id, "node_id": int(node_id)},
            ).mappings().first()
        if row is None:
            return None
        raw = row["meta_json"]
        if isinstance(raw, str):
            return json.loads(raw)
        return raw if isinstance(raw, dict) else None

    def list_for_tree(self, family_tree_id: str) -> List[Dict[str, Any]]:
        with self._engine.connect() as conn:
            rows = conn.execute(
                text(
                    "SELECT node_id, meta_json FROM family_tree_node_meta "
                    "WHERE family_tree_id = :tree_id ORDER BY node_id ASC"
                ),
                {"tree_id": family_tree_id},
            ).mappings().all()
        items: List[Dict[str, Any]] = []
        for row in rows:
            raw = row["meta_json"]
            meta = json.loads(raw) if isinstance(raw, str) else raw
            if isinstance(meta, dict):
                items.append({"node_id": int(row["node_id"]), "meta": meta})
        return items

    def delete_for_tree(self, family_tree_id: str) -> int:
        with self._engine.begin() as conn:
            result = conn.execute(
                text("DELETE FROM family_tree_node_meta WHERE family_tree_id = :tree_id"),
                {"tree_id": family_tree_id},
            )
        return int(result.rowcount or 0)

    def delete_node(self, family_tree_id: str, node_id: int) -> None:
        with self._engine.begin() as conn:
            conn.execute(
                text(
                    "DELETE FROM family_tree_node_meta "
                    "WHERE family_tree_id = :tree_id AND node_id = :node_id"
                ),
                {"tree_id": family_tree_id, "node_id": int(node_id)},
            )
