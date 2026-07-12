from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from sqlalchemy import select, text
from sqlalchemy.orm import Session

from app.balkan_node import strip_nodes_and_collect_meta
from app.node_meta.repository import NodeMetaRepository
from app.vgp.models import VgpCrawl
from tools.sync_vietnamgiapha_to_db import _normalize_nodes
from tools.vietnamgiapha_text_export import compute_nodes_hash


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


class VgpCrawlRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def get_content_hash(self, family_tree_id: str) -> Optional[str]:
        row = self.db.get(VgpCrawl, family_tree_id)
        return row.content_hash if row else None

    def get_crawl(self, family_tree_id: str) -> Optional[VgpCrawl]:
        return self.db.get(VgpCrawl, family_tree_id)

    def upsert_tree_and_crawl(
        self,
        *,
        family_tree_id: str,
        tree_id: int,
        name: str,
        description: Optional[str],
        external_url: str,
        raw_nodes: List[Dict[str, Any]],
        metadata: Dict[str, Any],
        manifest: Dict[str, Any],
        content_hash: str,
        nodes_hash: str,
        pha_ky_hash: Optional[str],
        has_source_document: bool,
    ) -> Dict[str, Any]:
        normalized_nodes = _normalize_nodes(raw_nodes)
        stripped_nodes, meta_map = strip_nodes_and_collect_meta(
            normalized_nodes,
            require_name_gender=False,
        )
        now = _now_iso()

        stmt = text(
            """
            INSERT INTO family_tree (
                id, name, description, nodes_json, node_count,
                external_url, has_source_document, created_at, updated_at
            )
            VALUES (
                :id, :name, :description, CAST(:nodes_json AS JSON), :node_count,
                :external_url, :has_source_document, :created_at, :updated_at
            )
            ON DUPLICATE KEY UPDATE
                name = VALUES(name),
                description = VALUES(description),
                nodes_json = VALUES(nodes_json),
                node_count = VALUES(node_count),
                external_url = VALUES(external_url),
                has_source_document = GREATEST(has_source_document, VALUES(has_source_document)),
                updated_at = VALUES(updated_at)
            """
        )
        self.db.execute(
            stmt,
            {
                "id": family_tree_id,
                "name": name,
                "description": description,
                "nodes_json": json.dumps(stripped_nodes, ensure_ascii=False),
                "node_count": len(stripped_nodes),
                "external_url": external_url,
                "has_source_document": 1 if has_source_document else 0,
                "created_at": now,
                "updated_at": now,
            },
        )

        meta_repo = NodeMetaRepository(self.db.get_bind())
        if meta_map:
            meta_repo.upsert_many(family_tree_id, meta_map)

        existing = self.get_crawl(family_tree_id)
        if existing is None:
            crawl = VgpCrawl(
                family_tree_id=family_tree_id,
                vgp_tree_id=tree_id,
                crawl_version="v2",
                manifest_json=manifest,
                metadata_json=metadata,
                content_hash=content_hash,
                nodes_hash=nodes_hash,
                pha_ky_hash=pha_ky_hash,
                fetched_at=now,
                updated_at=now,
            )
            self.db.add(crawl)
        else:
            existing.vgp_tree_id = tree_id
            existing.crawl_version = "v2"
            existing.manifest_json = manifest
            existing.metadata_json = metadata
            existing.content_hash = content_hash
            existing.nodes_hash = nodes_hash
            existing.pha_ky_hash = pha_ky_hash
            existing.fetched_at = now
            existing.updated_at = now

        self.db.flush()
        return {
            "family_tree_id": family_tree_id,
            "tree_id": tree_id,
            "node_count": len(stripped_nodes),
            "nodes_hash": nodes_hash,
            "content_hash": content_hash,
        }

    def compute_nodes_hash_from_raw(self, raw_nodes: List[Dict[str, Any]]) -> str:
        return compute_nodes_hash(_normalize_nodes(raw_nodes))
