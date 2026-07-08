from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from tempfile import NamedTemporaryFile
from threading import Lock
from typing import Any, Dict, List, Literal, Optional
from uuid import uuid4

from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine


class FamilyTreeStoreError(Exception):
    """Base exception for family tree persistence errors."""


class FamilyTreeNotFoundError(FamilyTreeStoreError):
    """Raised when a tree file does not exist."""


class FamilyTreeValidationError(FamilyTreeStoreError):
    """Raised when payload is invalid."""


def _default_external_url(tree_id: str) -> Optional[str]:
    clean = tree_id.strip()
    if clean.startswith("vpg-"):
        return f"https://vietnamgiapha.com/{clean}"
    return None


def _tree_metadata_from_doc(doc: Dict[str, Any]) -> Dict[str, Any]:
    external_url = doc.get("external_url")
    if not external_url:
        external_url = _default_external_url(str(doc.get("id") or ""))
    nodes = doc.get("nodes", [])
    from app.workspace.utils import compute_generation_count

    return {
        "external_url": external_url,
        "has_source_document": bool(doc.get("has_source_document", False)),
        "has_hannom_text": bool(doc.get("has_hannom_text", False)),
        "user_id": doc.get("user_id"),
        "is_public": bool(doc.get("is_public", False)),
        "generation_count": compute_generation_count(nodes if isinstance(nodes, list) else []),
    }


class _FamilyTreeStoreBase:
    """Shared business-logic helpers for all family tree store implementations."""

    # ------------------------------------------------------------------ #
    # Public CRUD API — subclasses must implement _load_tree / _persist   #
    # ------------------------------------------------------------------ #

    def list_trees(self) -> List[Dict[str, Any]]:
        raise NotImplementedError

    def create_tree(
        self,
        *,
        name: str,
        description: Optional[str] = None,
        nodes: Optional[List[Dict[str, Any]]] = None,
        external_url: Optional[str] = None,
        has_source_document: bool = False,
        has_hannom_text: bool = False,
        user_id: Optional[int] = None,
        is_public: bool = False,
    ) -> Dict[str, Any]:
        raise NotImplementedError

    def list_public_trees(self) -> List[Dict[str, Any]]:
        return [item for item in self.list_trees() if bool(item.get("is_public"))]

    def list_trees_by_user(self, user_id: int) -> List[Dict[str, Any]]:
        return [item for item in self.list_trees() if item.get("user_id") == user_id]

    def get_public_tree(self, tree_id: str) -> Dict[str, Any]:
        doc = self.get_tree(tree_id)
        if not bool(doc.get("is_public")):
            raise FamilyTreeNotFoundError(f"public tree '{tree_id}' not found")
        return doc

    def get_tree(self, tree_id: str) -> Dict[str, Any]:
        raise NotImplementedError

    def update_tree(
        self,
        tree_id: str,
        *,
        name: Optional[str] = None,
        description: Optional[str] = None,
        external_url: Optional[str] = None,
        has_source_document: Optional[bool] = None,
        has_hannom_text: Optional[bool] = None,
        is_public: Optional[bool] = None,
    ) -> Dict[str, Any]:
        raise NotImplementedError

    def replace_tree_document(
        self,
        tree_id: str,
        *,
        name: str,
        description: Optional[str],
        nodes: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        raise NotImplementedError

    def delete_tree(self, tree_id: str) -> None:
        raise NotImplementedError

    def add_node(self, tree_id: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        raise NotImplementedError

    def update_node(self, tree_id: str, node_id: int, payload: Dict[str, Any]) -> Dict[str, Any]:
        raise NotImplementedError

    def delete_node(self, tree_id: str, node_id: int) -> Dict[str, Any]:
        raise NotImplementedError

    def add_spouse_link(self, tree_id: str, from_id: int, to_id: int) -> Dict[str, Any]:
        raise NotImplementedError

    def delete_spouse_link(self, tree_id: str, from_id: int, to_id: int) -> Dict[str, Any]:
        raise NotImplementedError

    def add_parent_link(
        self,
        tree_id: str,
        *,
        parent_id: int,
        child_id: int,
        side: Literal["fid", "mid"],
    ) -> Dict[str, Any]:
        raise NotImplementedError

    def delete_parent_link(
        self,
        tree_id: str,
        *,
        parent_id: int,
        child_id: int,
        side: Optional[Literal["fid", "mid"]],
    ) -> Dict[str, Any]:
        raise NotImplementedError

    def _summary(self, doc: Dict[str, Any]) -> Dict[str, Any]:
        nodes = doc.get("nodes", [])
        summary: Dict[str, Any] = {
            "id": doc.get("id"),
            "name": doc.get("name"),
            "description": doc.get("description"),
            "created_at": doc.get("created_at"),
            "updated_at": doc.get("updated_at"),
            "node_count": len(nodes) if isinstance(nodes, list) else 0,
        }
        summary.update(_tree_metadata_from_doc(doc))
        return summary

    def _normalize_nodes(self, nodes: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        if not isinstance(nodes, list):
            raise FamilyTreeValidationError("nodes must be an array")

        normalized = [self._build_node_payload(item, node_id=item.get("id")) for item in nodes]
        ids = [int(n["id"]) for n in normalized]
        if len(set(ids)) != len(ids):
            raise FamilyTreeValidationError("duplicate node id detected")
        known_ids = set(ids)

        for node in normalized:
            for k in ("fid", "mid"):
                if k in node and node[k] not in known_ids:
                    raise FamilyTreeValidationError(f"{k}={node[k]} does not reference existing node")
            if "pids" in node:
                for pid in node["pids"]:
                    if pid not in known_ids:
                        raise FamilyTreeValidationError(f"pids contains unknown node id '{pid}'")
                    if pid == node["id"]:
                        raise FamilyTreeValidationError("pids cannot reference self")
        return normalized

    def _build_node_payload(
        self,
        payload: Dict[str, Any],
        *,
        node_id: Optional[Any],
        require_name_gender: bool = True,
    ) -> Dict[str, Any]:
        if not isinstance(payload, dict):
            raise FamilyTreeValidationError("node payload must be object")

        try:
            parsed_id = int(node_id)
        except (TypeError, ValueError):
            raise FamilyTreeValidationError("node id must be integer") from None
        if parsed_id <= 0:
            raise FamilyTreeValidationError("node id must be positive")

        name = payload.get("name")
        if require_name_gender and (not isinstance(name, str) or not name.strip()):
            raise FamilyTreeValidationError("node.name is required")

        gender = payload.get("gender")
        if require_name_gender and gender not in ("male", "female"):
            raise FamilyTreeValidationError("node.gender must be 'male' or 'female'")
        if gender is not None and gender not in ("male", "female"):
            raise FamilyTreeValidationError("node.gender must be 'male' or 'female'")

        node: Dict[str, Any] = {
            "id": parsed_id,
            "name": name.strip() if isinstance(name, str) else payload.get("name"),
        }
        if gender is not None:
            node["gender"] = gender

        if "birthYear" in payload and payload["birthYear"] is not None:
            node["birthYear"] = int(payload["birthYear"])

        if "deathYear" in payload and payload["deathYear"] is not None:
            node["deathYear"] = int(payload["deathYear"])

        for k in ("fid", "mid"):
            if payload.get(k) is not None:
                node[k] = int(payload[k])

        if "pids" in payload and payload["pids"] is not None:
            pids = payload["pids"]
            if not isinstance(pids, list):
                raise FamilyTreeValidationError("node.pids must be array")
            deduped = sorted(set(int(pid) for pid in pids if pid is not None))
            if deduped:
                node["pids"] = deduped

        # Preserve optional display fields if provided.
        for k in ("title", "avatar", "bio"):
            if k in payload and payload[k] is not None:
                node[k] = payload[k]

        return node

    def _node_index(self, nodes: List[Dict[str, Any]], node_id: int) -> int:
        for idx, item in enumerate(nodes):
            if int(item.get("id", -1)) == int(node_id):
                return idx
        return -1

    def _get_node(self, nodes: List[Dict[str, Any]], node_id: int) -> Optional[Dict[str, Any]]:
        idx = self._node_index(nodes, node_id)
        if idx == -1:
            return None
        return nodes[idx]

    def _ensure_node_exists(self, nodes: List[Dict[str, Any]], node_id: int) -> None:
        if self._node_index(nodes, node_id) == -1:
            raise FamilyTreeNotFoundError(f"node '{node_id}' not found")

    def _append_spouse(self, nodes: List[Dict[str, Any]], owner_id: int, spouse_id: int) -> None:
        node = self._get_node(nodes, owner_id)
        if node is None:
            raise FamilyTreeNotFoundError(f"node '{owner_id}' not found")

        pids = node.get("pids")
        if not isinstance(pids, list):
            pids = []
            node["pids"] = pids
        if spouse_id not in pids:
            pids.append(spouse_id)

    def _remove_spouse(self, nodes: List[Dict[str, Any]], owner_id: int, spouse_id: int) -> None:
        node = self._get_node(nodes, owner_id)
        if node is None:
            return

        pids = node.get("pids")
        if not isinstance(pids, list):
            return
        node["pids"] = [int(pid) for pid in pids if int(pid) != int(spouse_id)]
        if not node["pids"]:
            node.pop("pids", None)

    def _now_iso(self) -> str:
        return datetime.now(timezone.utc).isoformat()


# ---------------------------------------------------------------------------#
# File-based implementation (original)                                        #
# ---------------------------------------------------------------------------#

class JsonFamilyTreeStore(_FamilyTreeStoreBase):
    """File-based repository for family trees in Balkan node format."""

    def __init__(self, root_dir: Path) -> None:
        self._root_dir = root_dir
        self._root_dir.mkdir(parents=True, exist_ok=True)
        self._lock = Lock()

    # ------------------------------------------------------------------ #
    # Public CRUD API                                                      #
    # ------------------------------------------------------------------ #

    def list_trees(self) -> List[Dict[str, Any]]:
        with self._lock:
            items: List[Dict[str, Any]] = []
            for file in sorted(self._root_dir.glob("*.json")):
                doc = self._read_json(file)
                items.append(self._summary(doc))
            return items

    def create_tree(
        self,
        *,
        name: str,
        description: Optional[str] = None,
        nodes: Optional[List[Dict[str, Any]]] = None,
        external_url: Optional[str] = None,
        has_source_document: bool = False,
        has_hannom_text: bool = False,
        user_id: Optional[int] = None,
        is_public: bool = False,
    ) -> Dict[str, Any]:
        clean_name = name.strip()
        if not clean_name:
            raise FamilyTreeValidationError("name must not be empty")

        now = self._now_iso()
        tree_id = f"tree-{uuid4().hex[:8]}"
        normalized_nodes = self._normalize_nodes(nodes or [])
        doc: Dict[str, Any] = {
            "id": tree_id,
            "name": clean_name,
            "description": description,
            "created_at": now,
            "updated_at": now,
            "nodes": normalized_nodes,
            "external_url": (external_url.strip() if external_url else None) or _default_external_url(tree_id),
            "has_source_document": bool(has_source_document),
            "has_hannom_text": bool(has_hannom_text),
            "user_id": user_id,
            "is_public": bool(is_public),
        }

        with self._lock:
            self._write_json(self._file_path(tree_id), doc)
        return doc

    def get_tree(self, tree_id: str) -> Dict[str, Any]:
        with self._lock:
            return self._load_tree(tree_id)

    def update_tree(
        self,
        tree_id: str,
        *,
        name: Optional[str] = None,
        description: Optional[str] = None,
        external_url: Optional[str] = None,
        has_source_document: Optional[bool] = None,
        has_hannom_text: Optional[bool] = None,
        is_public: Optional[bool] = None,
    ) -> Dict[str, Any]:
        with self._lock:
            doc = self._load_tree(tree_id)
            if name is not None:
                clean_name = name.strip()
                if not clean_name:
                    raise FamilyTreeValidationError("name must not be empty")
                doc["name"] = clean_name
            if description is not None:
                doc["description"] = description
            if external_url is not None:
                doc["external_url"] = external_url.strip() or None
            if has_source_document is not None:
                doc["has_source_document"] = bool(has_source_document)
            if has_hannom_text is not None:
                doc["has_hannom_text"] = bool(has_hannom_text)
            if is_public is not None:
                doc["is_public"] = bool(is_public)
            doc["updated_at"] = self._now_iso()
            self._write_json(self._file_path(tree_id), doc)
            return doc

    def replace_tree_document(
        self,
        tree_id: str,
        *,
        name: str,
        description: Optional[str],
        nodes: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        clean_name = name.strip()
        if not clean_name:
            raise FamilyTreeValidationError("name must not be empty")

        with self._lock:
            doc = self._load_tree(tree_id)
            doc["name"] = clean_name
            doc["description"] = description
            doc["nodes"] = self._normalize_nodes(nodes)
            doc["updated_at"] = self._now_iso()
            self._write_json(self._file_path(tree_id), doc)
            return doc

    def delete_tree(self, tree_id: str) -> None:
        with self._lock:
            path = self._file_path(tree_id)
            if not path.exists():
                raise FamilyTreeNotFoundError(f"tree '{tree_id}' not found")
            path.unlink()

    def add_node(self, tree_id: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        with self._lock:
            doc = self._load_tree(tree_id)
            nodes = doc.get("nodes", [])
            next_id = max([int(n["id"]) for n in nodes], default=0) + 1

            node = self._build_node_payload(payload, node_id=next_id)
            nodes.append(node)
            self._normalize_nodes(nodes)
            doc["updated_at"] = self._now_iso()
            self._write_json(self._file_path(tree_id), doc)
            return doc

    def update_node(self, tree_id: str, node_id: int, payload: Dict[str, Any]) -> Dict[str, Any]:
        with self._lock:
            doc = self._load_tree(tree_id)
            nodes = doc.get("nodes", [])
            idx = self._node_index(nodes, node_id)
            if idx == -1:
                raise FamilyTreeNotFoundError(f"node '{node_id}' not found")

            current = nodes[idx]
            merged = {**current, **payload, "id": int(node_id)}
            nodes[idx] = self._build_node_payload(merged, node_id=int(node_id), require_name_gender=False)
            self._normalize_nodes(nodes)
            doc["updated_at"] = self._now_iso()
            self._write_json(self._file_path(tree_id), doc)
            return doc

    def delete_node(self, tree_id: str, node_id: int) -> Dict[str, Any]:
        with self._lock:
            doc = self._load_tree(tree_id)
            nodes = doc.get("nodes", [])
            idx = self._node_index(nodes, node_id)
            if idx == -1:
                raise FamilyTreeNotFoundError(f"node '{node_id}' not found")

            nodes.pop(idx)
            for node in nodes:
                if node.get("fid") == node_id:
                    node.pop("fid", None)
                if node.get("mid") == node_id:
                    node.pop("mid", None)
                pids = node.get("pids")
                if isinstance(pids, list):
                    node["pids"] = [int(pid) for pid in pids if int(pid) != node_id]
                    if not node["pids"]:
                        node.pop("pids", None)

            self._normalize_nodes(nodes)
            doc["updated_at"] = self._now_iso()
            self._write_json(self._file_path(tree_id), doc)
            return doc

    def add_spouse_link(self, tree_id: str, from_id: int, to_id: int) -> Dict[str, Any]:
        if from_id == to_id:
            raise FamilyTreeValidationError("spouse link cannot point to itself")

        with self._lock:
            doc = self._load_tree(tree_id)
            nodes = doc.get("nodes", [])
            self._ensure_node_exists(nodes, from_id)
            self._ensure_node_exists(nodes, to_id)

            self._append_spouse(nodes, from_id, to_id)
            self._append_spouse(nodes, to_id, from_id)
            self._normalize_nodes(nodes)
            doc["updated_at"] = self._now_iso()
            self._write_json(self._file_path(tree_id), doc)
            return doc

    def delete_spouse_link(self, tree_id: str, from_id: int, to_id: int) -> Dict[str, Any]:
        with self._lock:
            doc = self._load_tree(tree_id)
            nodes = doc.get("nodes", [])
            self._remove_spouse(nodes, from_id, to_id)
            self._remove_spouse(nodes, to_id, from_id)
            self._normalize_nodes(nodes)
            doc["updated_at"] = self._now_iso()
            self._write_json(self._file_path(tree_id), doc)
            return doc

    def add_parent_link(
        self,
        tree_id: str,
        *,
        parent_id: int,
        child_id: int,
        side: Literal["fid", "mid"],
    ) -> Dict[str, Any]:
        if parent_id == child_id:
            raise FamilyTreeValidationError("parent link cannot point to itself")

        with self._lock:
            doc = self._load_tree(tree_id)
            nodes = doc.get("nodes", [])
            self._ensure_node_exists(nodes, parent_id)
            child = self._get_node(nodes, child_id)
            if child is None:
                raise FamilyTreeNotFoundError(f"node '{child_id}' not found")

            child[side] = int(parent_id)
            self._normalize_nodes(nodes)
            doc["updated_at"] = self._now_iso()
            self._write_json(self._file_path(tree_id), doc)
            return doc

    def delete_parent_link(
        self,
        tree_id: str,
        *,
        parent_id: int,
        child_id: int,
        side: Optional[Literal["fid", "mid"]],
    ) -> Dict[str, Any]:
        with self._lock:
            doc = self._load_tree(tree_id)
            nodes = doc.get("nodes", [])
            child = self._get_node(nodes, child_id)
            if child is None:
                raise FamilyTreeNotFoundError(f"node '{child_id}' not found")

            if side in ("fid", "mid"):
                if child.get(side) == int(parent_id):
                    child.pop(side, None)
            else:
                for k in ("fid", "mid"):
                    if child.get(k) == int(parent_id):
                        child.pop(k, None)

            self._normalize_nodes(nodes)
            doc["updated_at"] = self._now_iso()
            self._write_json(self._file_path(tree_id), doc)
            return doc

    # ------------------------------------------------------------------ #
    # File-specific helpers                                                #
    # ------------------------------------------------------------------ #

    def _load_tree(self, tree_id: str) -> Dict[str, Any]:
        path = self._file_path(tree_id)
        if not path.exists():
            raise FamilyTreeNotFoundError(f"tree '{tree_id}' not found")
        doc = self._read_json(path)
        if doc.get("id") != tree_id:
            raise FamilyTreeValidationError(f"tree file '{tree_id}' is malformed")
        doc["nodes"] = self._normalize_nodes(doc.get("nodes", []))
        return doc

    def _file_path(self, tree_id: str) -> Path:
        return self._root_dir / f"{tree_id}.json"

    def _read_json(self, path: Path) -> Dict[str, Any]:
        with path.open("r", encoding="utf-8") as fh:
            data = json.load(fh)
        if not isinstance(data, dict):
            raise FamilyTreeValidationError(f"{path.name}: expected object")
        return data

    def _write_json(self, path: Path, data: Dict[str, Any]) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        with NamedTemporaryFile("w", delete=False, dir=path.parent, encoding="utf-8") as tmp:
            json.dump(data, tmp, ensure_ascii=False, indent=2)
            tmp.write("\n")
            temp_name = tmp.name
        Path(temp_name).replace(path)


# ---------------------------------------------------------------------------#
# MySQL-backed implementation                                                  #
# ---------------------------------------------------------------------------#

class MySqlFamilyTreeStore(_FamilyTreeStoreBase):
    """MySQL-backed repository storing each family tree as a row with JSON nodes.

    Schema (auto-created on first use):
        family_tree (
            id          VARCHAR(64)  PRIMARY KEY,
            name        VARCHAR(255) NOT NULL,
            description TEXT         NULL,
            nodes_json  JSON         NOT NULL,
            node_count  INT          NOT NULL DEFAULT 0,
            created_at  VARCHAR(64)  NOT NULL,
            updated_at  VARCHAR(64)  NOT NULL
        )
    """

    def __init__(self, engine: Engine) -> None:
        self._engine = engine
        self._lock = Lock()
        self._ensure_schema()

    @classmethod
    def from_env(cls) -> "MySqlFamilyTreeStore":
        mysql_host = os.getenv("MYSQL_HOST")
        mysql_port = os.getenv("MYSQL_PORT", "3306")
        mysql_db = os.getenv("MYSQL_DATABASE", "family_tree")
        mysql_user = os.getenv("MYSQL_USER")
        mysql_password = os.getenv("MYSQL_PASSWORD")

        if not mysql_host or not mysql_user or not mysql_password:
            raise RuntimeError("MYSQL_HOST, MYSQL_USER, MYSQL_PASSWORD env vars are required")

        url = (
            f"mysql+pymysql://{mysql_user}:{mysql_password}@{mysql_host}:{mysql_port}/{mysql_db}"
            "?charset=utf8mb4"
        )
        engine = create_engine(url, pool_pre_ping=True, future=True)
        return cls(engine)

    def _ensure_schema(self) -> None:
        ddl = """
        CREATE TABLE IF NOT EXISTS family_tree (
            id          VARCHAR(64)  NOT NULL PRIMARY KEY,
            name        VARCHAR(255) NOT NULL,
            description TEXT         NULL,
            nodes_json  JSON         NOT NULL,
            node_count  INT          NOT NULL DEFAULT 0,
            external_url VARCHAR(512) NULL,
            has_source_document TINYINT(1) NOT NULL DEFAULT 0,
            has_hannom_text TINYINT(1) NOT NULL DEFAULT 0,
            created_at  VARCHAR(64)  NOT NULL,
            updated_at  VARCHAR(64)  NOT NULL,
            created_ts  TIMESTAMP    DEFAULT CURRENT_TIMESTAMP,
            updated_ts  TIMESTAMP    DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
        """
        with self._engine.begin() as conn:
            conn.execute(text(ddl))
            self._migrate_schema(conn)

    def _migrate_schema(self, conn) -> None:
        existing = {
            row[0]
            for row in conn.execute(text("SHOW COLUMNS FROM family_tree")).fetchall()
        }
        migrations = [
            ("external_url", "ALTER TABLE family_tree ADD COLUMN external_url VARCHAR(512) NULL"),
            (
                "has_source_document",
                "ALTER TABLE family_tree ADD COLUMN has_source_document TINYINT(1) NOT NULL DEFAULT 0",
            ),
            (
                "has_hannom_text",
                "ALTER TABLE family_tree ADD COLUMN has_hannom_text TINYINT(1) NOT NULL DEFAULT 0",
            ),
            ("user_id", "ALTER TABLE family_tree ADD COLUMN user_id INT NULL"),
            (
                "is_public",
                "ALTER TABLE family_tree ADD COLUMN is_public TINYINT(1) NOT NULL DEFAULT 0",
            ),
        ]
        for column_name, statement in migrations:
            if column_name not in existing:
                conn.execute(text(statement))
                existing.add(column_name)
        if "is_public" in existing:
            conn.execute(
                text("UPDATE family_tree SET is_public = 1 WHERE id LIKE 'vpg-%' AND is_public = 0")
            )

    # ------------------------------------------------------------------ #
    # Public CRUD API                                                      #
    # ------------------------------------------------------------------ #

    def list_trees(self) -> List[Dict[str, Any]]:
        return self._list_trees_query()

    def list_public_trees(self) -> List[Dict[str, Any]]:
        return self._list_trees_query(public_only=True)

    def list_trees_by_user(self, user_id: int) -> List[Dict[str, Any]]:
        return self._list_trees_query(user_id=user_id)

    def _list_trees_query(
        self,
        *,
        public_only: bool = False,
        user_id: Optional[int] = None,
    ) -> List[Dict[str, Any]]:
        clauses = []
        params: Dict[str, Any] = {}
        if public_only:
            clauses.append("is_public = 1")
        if user_id is not None:
            clauses.append("user_id = :user_id")
            params["user_id"] = user_id
        where_sql = f"WHERE {' AND '.join(clauses)}" if clauses else ""
        with self._lock:
            with self._engine.connect() as conn:
                rows = conn.execute(
                    text(
                        "SELECT id, name, description, created_at, updated_at, node_count, "
                        "external_url, has_source_document, has_hannom_text, user_id, is_public "
                        f"FROM family_tree {where_sql} ORDER BY created_ts ASC"
                    ),
                    params,
                ).mappings().all()
            return [self._row_to_summary(r) for r in rows]

    def _row_to_summary(self, row: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "id": row["id"],
            "name": row["name"],
            "description": row["description"],
            "created_at": row["created_at"],
            "updated_at": row["updated_at"],
            "node_count": row["node_count"],
            "external_url": row.get("external_url") or _default_external_url(str(row["id"])),
            "has_source_document": bool(row.get("has_source_document", 0)),
            "has_hannom_text": bool(row.get("has_hannom_text", 0)),
            "user_id": row.get("user_id"),
            "is_public": bool(row.get("is_public", 0)),
            "generation_count": 0,
        }

    def create_tree(
        self,
        *,
        name: str,
        description: Optional[str] = None,
        nodes: Optional[List[Dict[str, Any]]] = None,
        external_url: Optional[str] = None,
        has_source_document: bool = False,
        has_hannom_text: bool = False,
        user_id: Optional[int] = None,
        is_public: bool = False,
    ) -> Dict[str, Any]:
        clean_name = name.strip()
        if not clean_name:
            raise FamilyTreeValidationError("name must not be empty")

        now = self._now_iso()
        tree_id = f"tree-{uuid4().hex[:8]}"
        normalized_nodes = self._normalize_nodes(nodes or [])
        doc: Dict[str, Any] = {
            "id": tree_id,
            "name": clean_name,
            "description": description,
            "created_at": now,
            "updated_at": now,
            "nodes": normalized_nodes,
            "external_url": (external_url.strip() if external_url else None) or _default_external_url(tree_id),
            "has_source_document": bool(has_source_document),
            "has_hannom_text": bool(has_hannom_text),
            "user_id": user_id,
            "is_public": bool(is_public),
        }

        with self._lock:
            self._db_insert(doc)
        return doc

    def get_tree(self, tree_id: str) -> Dict[str, Any]:
        with self._lock:
            return self._load_tree(tree_id)

    def update_tree(
        self,
        tree_id: str,
        *,
        name: Optional[str] = None,
        description: Optional[str] = None,
        external_url: Optional[str] = None,
        has_source_document: Optional[bool] = None,
        has_hannom_text: Optional[bool] = None,
        is_public: Optional[bool] = None,
    ) -> Dict[str, Any]:
        with self._lock:
            doc = self._load_tree(tree_id)
            if name is not None:
                clean_name = name.strip()
                if not clean_name:
                    raise FamilyTreeValidationError("name must not be empty")
                doc["name"] = clean_name
            if description is not None:
                doc["description"] = description
            if external_url is not None:
                doc["external_url"] = external_url.strip() or None
            if has_source_document is not None:
                doc["has_source_document"] = bool(has_source_document)
            if has_hannom_text is not None:
                doc["has_hannom_text"] = bool(has_hannom_text)
            if is_public is not None:
                doc["is_public"] = bool(is_public)
            doc["updated_at"] = self._now_iso()
            self._db_save(doc)
            return doc

    def replace_tree_document(
        self,
        tree_id: str,
        *,
        name: str,
        description: Optional[str],
        nodes: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        clean_name = name.strip()
        if not clean_name:
            raise FamilyTreeValidationError("name must not be empty")

        with self._lock:
            doc = self._load_tree(tree_id)
            doc["name"] = clean_name
            doc["description"] = description
            doc["nodes"] = self._normalize_nodes(nodes)
            doc["updated_at"] = self._now_iso()
            self._db_save(doc)
            return doc

    def delete_tree(self, tree_id: str) -> None:
        with self._lock:
            with self._engine.begin() as conn:
                result = conn.execute(
                    text("DELETE FROM family_tree WHERE id = :id"),
                    {"id": tree_id},
                )
            if result.rowcount == 0:
                raise FamilyTreeNotFoundError(f"tree '{tree_id}' not found")

    def add_node(self, tree_id: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        with self._lock:
            doc = self._load_tree(tree_id)
            nodes = doc.get("nodes", [])
            next_id = max([int(n["id"]) for n in nodes], default=0) + 1

            node = self._build_node_payload(payload, node_id=next_id)
            nodes.append(node)
            self._normalize_nodes(nodes)
            doc["updated_at"] = self._now_iso()
            self._db_save(doc)
            return doc

    def update_node(self, tree_id: str, node_id: int, payload: Dict[str, Any]) -> Dict[str, Any]:
        with self._lock:
            doc = self._load_tree(tree_id)
            nodes = doc.get("nodes", [])
            idx = self._node_index(nodes, node_id)
            if idx == -1:
                raise FamilyTreeNotFoundError(f"node '{node_id}' not found")

            current = nodes[idx]
            merged = {**current, **payload, "id": int(node_id)}
            nodes[idx] = self._build_node_payload(merged, node_id=int(node_id), require_name_gender=False)
            self._normalize_nodes(nodes)
            doc["updated_at"] = self._now_iso()
            self._db_save(doc)
            return doc

    def delete_node(self, tree_id: str, node_id: int) -> Dict[str, Any]:
        with self._lock:
            doc = self._load_tree(tree_id)
            nodes = doc.get("nodes", [])
            idx = self._node_index(nodes, node_id)
            if idx == -1:
                raise FamilyTreeNotFoundError(f"node '{node_id}' not found")

            nodes.pop(idx)
            for node in nodes:
                if node.get("fid") == node_id:
                    node.pop("fid", None)
                if node.get("mid") == node_id:
                    node.pop("mid", None)
                pids = node.get("pids")
                if isinstance(pids, list):
                    node["pids"] = [int(pid) for pid in pids if int(pid) != node_id]
                    if not node["pids"]:
                        node.pop("pids", None)

            self._normalize_nodes(nodes)
            doc["updated_at"] = self._now_iso()
            self._db_save(doc)
            return doc

    def add_spouse_link(self, tree_id: str, from_id: int, to_id: int) -> Dict[str, Any]:
        if from_id == to_id:
            raise FamilyTreeValidationError("spouse link cannot point to itself")

        with self._lock:
            doc = self._load_tree(tree_id)
            nodes = doc.get("nodes", [])
            self._ensure_node_exists(nodes, from_id)
            self._ensure_node_exists(nodes, to_id)

            self._append_spouse(nodes, from_id, to_id)
            self._append_spouse(nodes, to_id, from_id)
            self._normalize_nodes(nodes)
            doc["updated_at"] = self._now_iso()
            self._db_save(doc)
            return doc

    def delete_spouse_link(self, tree_id: str, from_id: int, to_id: int) -> Dict[str, Any]:
        with self._lock:
            doc = self._load_tree(tree_id)
            nodes = doc.get("nodes", [])
            self._remove_spouse(nodes, from_id, to_id)
            self._remove_spouse(nodes, to_id, from_id)
            self._normalize_nodes(nodes)
            doc["updated_at"] = self._now_iso()
            self._db_save(doc)
            return doc

    def add_parent_link(
        self,
        tree_id: str,
        *,
        parent_id: int,
        child_id: int,
        side: Literal["fid", "mid"],
    ) -> Dict[str, Any]:
        if parent_id == child_id:
            raise FamilyTreeValidationError("parent link cannot point to itself")

        with self._lock:
            doc = self._load_tree(tree_id)
            nodes = doc.get("nodes", [])
            self._ensure_node_exists(nodes, parent_id)
            child = self._get_node(nodes, child_id)
            if child is None:
                raise FamilyTreeNotFoundError(f"node '{child_id}' not found")

            child[side] = int(parent_id)
            self._normalize_nodes(nodes)
            doc["updated_at"] = self._now_iso()
            self._db_save(doc)
            return doc

    def delete_parent_link(
        self,
        tree_id: str,
        *,
        parent_id: int,
        child_id: int,
        side: Optional[Literal["fid", "mid"]],
    ) -> Dict[str, Any]:
        with self._lock:
            doc = self._load_tree(tree_id)
            nodes = doc.get("nodes", [])
            child = self._get_node(nodes, child_id)
            if child is None:
                raise FamilyTreeNotFoundError(f"node '{child_id}' not found")

            if side in ("fid", "mid"):
                if child.get(side) == int(parent_id):
                    child.pop(side, None)
            else:
                for k in ("fid", "mid"):
                    if child.get(k) == int(parent_id):
                        child.pop(k, None)

            self._normalize_nodes(nodes)
            doc["updated_at"] = self._now_iso()
            self._db_save(doc)
            return doc

    # ------------------------------------------------------------------ #
    # MySQL helpers                                                        #
    # ------------------------------------------------------------------ #

    def _load_tree(self, tree_id: str) -> Dict[str, Any]:
        with self._engine.connect() as conn:
            row = conn.execute(
                text(
                    "SELECT id, name, description, nodes_json, created_at, updated_at, "
                    "external_url, has_source_document, has_hannom_text, user_id, is_public "
                    "FROM family_tree WHERE id = :id"
                ),
                {"id": tree_id},
            ).mappings().first()
        if row is None:
            raise FamilyTreeNotFoundError(f"tree '{tree_id}' not found")
        raw_nodes = row["nodes_json"]
        nodes = json.loads(raw_nodes) if isinstance(raw_nodes, str) else raw_nodes
        doc: Dict[str, Any] = {
            "id": row["id"],
            "name": row["name"],
            "description": row["description"],
            "created_at": row["created_at"],
            "updated_at": row["updated_at"],
            "nodes": self._normalize_nodes(nodes if isinstance(nodes, list) else []),
            "external_url": row.get("external_url") or _default_external_url(str(row["id"])),
            "has_source_document": bool(row.get("has_source_document", 0)),
            "has_hannom_text": bool(row.get("has_hannom_text", 0)),
            "user_id": row.get("user_id"),
            "is_public": bool(row.get("is_public", 0)),
        }
        return doc

    def _db_insert(self, doc: Dict[str, Any]) -> None:
        nodes_json = json.dumps(doc["nodes"], ensure_ascii=False)
        with self._engine.begin() as conn:
            conn.execute(
                text(
                    "INSERT INTO family_tree "
                    "(id, name, description, nodes_json, node_count, external_url, "
                    "has_source_document, has_hannom_text, user_id, is_public, created_at, updated_at) "
                    "VALUES (:id, :name, :description, CAST(:nodes_json AS JSON), :node_count, "
                    ":external_url, :has_source_document, :has_hannom_text, :user_id, :is_public, "
                    ":created_at, :updated_at)"
                ),
                {
                    "id": doc["id"],
                    "name": doc["name"],
                    "description": doc.get("description"),
                    "nodes_json": nodes_json,
                    "node_count": len(doc["nodes"]),
                    "external_url": doc.get("external_url"),
                    "has_source_document": int(bool(doc.get("has_source_document", False))),
                    "has_hannom_text": int(bool(doc.get("has_hannom_text", False))),
                    "user_id": doc.get("user_id"),
                    "is_public": int(bool(doc.get("is_public", False))),
                    "created_at": doc["created_at"],
                    "updated_at": doc["updated_at"],
                },
            )

    def _db_save(self, doc: Dict[str, Any]) -> None:
        nodes_json = json.dumps(doc["nodes"], ensure_ascii=False)
        with self._engine.begin() as conn:
            conn.execute(
                text(
                    "UPDATE family_tree "
                    "SET name = :name, description = :description, "
                    "    nodes_json = CAST(:nodes_json AS JSON), node_count = :node_count, "
                    "    external_url = :external_url, "
                    "    has_source_document = :has_source_document, "
                    "    has_hannom_text = :has_hannom_text, "
                    "    user_id = :user_id, is_public = :is_public, "
                    "    updated_at = :updated_at "
                    "WHERE id = :id"
                ),
                {
                    "id": doc["id"],
                    "name": doc["name"],
                    "description": doc.get("description"),
                    "nodes_json": nodes_json,
                    "node_count": len(doc["nodes"]),
                    "external_url": doc.get("external_url"),
                    "has_source_document": int(bool(doc.get("has_source_document", False))),
                    "has_hannom_text": int(bool(doc.get("has_hannom_text", False))),
                    "user_id": doc.get("user_id"),
                    "is_public": int(bool(doc.get("is_public", False))),
                    "updated_at": doc["updated_at"],
                },
            )


class MirroredFamilyTreeStore:
    """Store wrapper that reads from primary store and mirrors writes to source JSON files."""

    def __init__(self, *, primary_store: _FamilyTreeStoreBase, source_store: JsonFamilyTreeStore) -> None:
        self._primary = primary_store
        self._source = source_store

    def list_trees(self) -> List[Dict[str, Any]]:
        return self._primary.list_trees()

    def list_public_trees(self) -> List[Dict[str, Any]]:
        return self._primary.list_public_trees()

    def list_trees_by_user(self, user_id: int) -> List[Dict[str, Any]]:
        return self._primary.list_trees_by_user(user_id)

    def get_public_tree(self, tree_id: str) -> Dict[str, Any]:
        return self._primary.get_public_tree(tree_id)

    def create_tree(
        self,
        *,
        name: str,
        description: Optional[str] = None,
        nodes: Optional[List[Dict[str, Any]]] = None,
        external_url: Optional[str] = None,
        has_source_document: bool = False,
        has_hannom_text: bool = False,
        user_id: Optional[int] = None,
        is_public: bool = False,
    ) -> Dict[str, Any]:
        doc = self._primary.create_tree(
            name=name,
            description=description,
            nodes=nodes,
            external_url=external_url,
            has_source_document=has_source_document,
            has_hannom_text=has_hannom_text,
            user_id=user_id,
            is_public=is_public,
        )
        self._sync_source_document(doc)
        return doc

    def get_tree(self, tree_id: str) -> Dict[str, Any]:
        return self._primary.get_tree(tree_id)

    def update_tree(
        self,
        tree_id: str,
        *,
        name: Optional[str] = None,
        description: Optional[str] = None,
        external_url: Optional[str] = None,
        has_source_document: Optional[bool] = None,
        has_hannom_text: Optional[bool] = None,
        is_public: Optional[bool] = None,
    ) -> Dict[str, Any]:
        doc = self._primary.update_tree(
            tree_id,
            name=name,
            description=description,
            external_url=external_url,
            has_source_document=has_source_document,
            has_hannom_text=has_hannom_text,
            is_public=is_public,
        )
        self._sync_source_document(doc)
        return doc

    def replace_tree_document(
        self,
        tree_id: str,
        *,
        name: str,
        description: Optional[str],
        nodes: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        doc = self._primary.replace_tree_document(
            tree_id,
            name=name,
            description=description,
            nodes=nodes,
        )
        self._sync_source_document(doc)
        return doc

    def delete_tree(self, tree_id: str) -> None:
        self._primary.delete_tree(tree_id)
        self._delete_source_document(tree_id)

    def add_node(self, tree_id: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        doc = self._primary.add_node(tree_id, payload)
        self._sync_source_document(doc)
        return doc

    def update_node(self, tree_id: str, node_id: int, payload: Dict[str, Any]) -> Dict[str, Any]:
        doc = self._primary.update_node(tree_id, node_id, payload)
        self._sync_source_document(doc)
        return doc

    def delete_node(self, tree_id: str, node_id: int) -> Dict[str, Any]:
        doc = self._primary.delete_node(tree_id, node_id)
        self._sync_source_document(doc)
        return doc

    def add_spouse_link(self, tree_id: str, from_id: int, to_id: int) -> Dict[str, Any]:
        doc = self._primary.add_spouse_link(tree_id, from_id, to_id)
        self._sync_source_document(doc)
        return doc

    def delete_spouse_link(self, tree_id: str, from_id: int, to_id: int) -> Dict[str, Any]:
        doc = self._primary.delete_spouse_link(tree_id, from_id, to_id)
        self._sync_source_document(doc)
        return doc

    def add_parent_link(
        self,
        tree_id: str,
        *,
        parent_id: int,
        child_id: int,
        side: Literal["fid", "mid"],
    ) -> Dict[str, Any]:
        doc = self._primary.add_parent_link(
            tree_id,
            parent_id=parent_id,
            child_id=child_id,
            side=side,
        )
        self._sync_source_document(doc)
        return doc

    def delete_parent_link(
        self,
        tree_id: str,
        *,
        parent_id: int,
        child_id: int,
        side: Optional[Literal["fid", "mid"]],
    ) -> Dict[str, Any]:
        doc = self._primary.delete_parent_link(
            tree_id,
            parent_id=parent_id,
            child_id=child_id,
            side=side,
        )
        self._sync_source_document(doc)
        return doc

    def _sync_source_document(self, doc: Dict[str, Any]) -> None:
        try:
            tree_id = str(doc.get("id") or "")
            if not tree_id:
                raise FamilyTreeValidationError("tree.id is required for source sync")

            source_doc: Dict[str, Any] = {
                "id": tree_id,
                "name": doc.get("name"),
                "description": doc.get("description"),
                "created_at": doc.get("created_at"),
                "updated_at": doc.get("updated_at"),
                "nodes": self._source._normalize_nodes(doc.get("nodes", [])),
                "external_url": doc.get("external_url"),
                "has_source_document": doc.get("has_source_document", False),
                "has_hannom_text": doc.get("has_hannom_text", False),
            }
            with self._source._lock:
                self._source._write_json(self._source._file_path(tree_id), source_doc)
        except Exception as exc:  # pragma: no cover - sync safety
            raise FamilyTreeStoreError(f"Failed to sync source JSON for tree '{doc.get('id')}'") from exc

    def _delete_source_document(self, tree_id: str) -> None:
        try:
            with self._source._lock:
                path = self._source._file_path(tree_id)
                if path.exists():
                    path.unlink()
        except Exception as exc:  # pragma: no cover - sync safety
            raise FamilyTreeStoreError(f"Failed to delete source JSON for tree '{tree_id}'") from exc
