"""Crawl a single vietnamgiapha.com tree (meta + phả ký + sơ đồ)."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from label_studio_pipeline.corpus_store import (
    compute_tree_content_hash,
    load_json,
    save_tree_corpus,
    tree_dir,
)
from label_studio_pipeline.html_utils import extract_giapha_meta, extract_legacy_content, fetch_html_optional
from label_studio_pipeline.pha_he_parser import parse_pha_he_html
from label_studio_pipeline.vgp_urls import giapha_url, pha_he_legacy_url, pha_he_url, pha_ky_url

logger = logging.getLogger(__name__)


@dataclass
class TreeCrawlResult:
    tree_id: int
    status: str
    reason: str | None = None
    output_dir: str | None = None
    pha_ky_chars: int = 0
    pha_he_nodes: int = 0
    content_hash: str | None = None


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def crawl_tree(
    tree_id: int,
    *,
    corpus_root: Path,
    timeout: float = 30.0,
    skip_unchanged: bool = True,
    min_pha_ky_chars: int = 1,
) -> TreeCrawlResult:
    """
    Fetch giapha + phả ký + phả hệ for one ``tree_id`` and persist under corpus_root.

    Returns status: ``saved``, ``skipped_unchanged``, ``skipped_empty``, ``error``.
    """
    existing_meta = load_json(tree_dir(corpus_root, tree_id) / "meta.json")

    giapha_html, giapha_status = fetch_html_optional(giapha_url(tree_id), timeout=timeout)
    if giapha_html is None:
        return TreeCrawlResult(
            tree_id=tree_id,
            status="skipped_empty",
            reason=f"giapha unavailable (status={giapha_status})",
        )

    meta_fields = extract_giapha_meta(giapha_html)
    meta: dict[str, Any] = {
        "giapha_url": giapha_url(tree_id),
        "pha_ky_url": pha_ky_url(tree_id),
        "pha_he_url": pha_he_url(tree_id),
        **meta_fields,
    }

    pha_ky_html, _ = fetch_html_optional(pha_ky_url(tree_id), timeout=timeout)
    pha_ky_text = extract_legacy_content(pha_ky_html or "")

    pha_he_html, _ = fetch_html_optional(pha_he_url(tree_id), timeout=timeout)
    pha_he_source = pha_he_url(tree_id)
    if not pha_he_html or parse_pha_he_html(pha_he_html, tree_id=tree_id, source_url=pha_he_source).get("node_count", 0) == 0:
        legacy_html, _ = fetch_html_optional(pha_he_legacy_url(tree_id), timeout=timeout)
        if legacy_html:
            pha_he_html = legacy_html
            pha_he_source = pha_he_legacy_url(tree_id)

    if not pha_he_html:
        pha_he_payload: dict[str, Any] = {
            "tree_id": tree_id,
            "source_url": pha_he_url(tree_id),
            "lineage_name": meta_fields.get("lineage_name"),
            "parser_mode": "none",
            "node_count": 0,
            "relationship_count": 0,
            "nodes": [],
            "relationships": [],
        }
    else:
        pha_he_payload = parse_pha_he_html(pha_he_html, tree_id=tree_id, source_url=pha_he_source)

    has_pha_ky = len(pha_ky_text) >= min_pha_ky_chars
    has_pha_he = int(pha_he_payload.get("node_count") or 0) > 0

    if not has_pha_ky and not has_pha_he:
        return TreeCrawlResult(
            tree_id=tree_id,
            status="skipped_empty",
            reason="no pha_ky text and no pha_he nodes",
        )

    content_hash = compute_tree_content_hash(pha_ky_text=pha_ky_text, pha_he_payload=pha_he_payload)
    if skip_unchanged and existing_meta and existing_meta.get("content_hash") == content_hash:
        return TreeCrawlResult(
            tree_id=tree_id,
            status="skipped_unchanged",
            reason="content_hash unchanged",
            output_dir=str(tree_dir(corpus_root, tree_id)),
            pha_ky_chars=len(pha_ky_text),
            pha_he_nodes=int(pha_he_payload.get("node_count") or 0),
            content_hash=content_hash,
        )

    out_dir = save_tree_corpus(
        corpus_root,
        tree_id=tree_id,
        meta=meta,
        pha_ky_text=pha_ky_text,
        pha_he_payload=pha_he_payload,
        content_hash=content_hash,
    )
    logger.info(
        "Saved tree_id=%s pha_ky_chars=%d pha_he_nodes=%d",
        tree_id,
        len(pha_ky_text),
        pha_he_payload.get("node_count", 0),
    )
    return TreeCrawlResult(
        tree_id=tree_id,
        status="saved",
        output_dir=str(out_dir),
        pha_ky_chars=len(pha_ky_text),
        pha_he_nodes=int(pha_he_payload.get("node_count") or 0),
        content_hash=content_hash,
    )
