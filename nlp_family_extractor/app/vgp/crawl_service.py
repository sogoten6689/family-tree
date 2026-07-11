from __future__ import annotations

import mimetypes
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from io import BytesIO
from typing import Any, Callable, Dict, List, Optional, Set

import httpx
from sqlalchemy.orm import Session

from app.documents.repository import DocumentRepository, DocumentService
from app.documents.storage import ObjectStorage
from app.pipeline.service import PipelineService
from app.vgp.parsers import (
    compute_vgp_content_hash,
    hash_text,
    parse_giapha,
    parse_images,
    parse_pha_he,
    parse_pha_ky_text,
)
from app.vgp.repository import VgpCrawlRepository
from app.vgp.urls import (
    giapha_url,
    hinh_anh_url,
    pha_he_legacy_url,
    pha_he_url,
    pha_ky_url,
    store_id,
)
from tools.sync_vietnamgiapha_documents import (
    VGP_HINH_ANH_MARKER,
    VGP_PHA_KY_MARKER,
    attach_vgp_images_document,
    attach_vgp_pha_ky_document,
)

DEFAULT_MODULES = ("giapha", "pha_ky", "pha_he", "images")
USER_AGENT = "FamilyTreeVgpCrawler/2.0 (+https://github.com/family-tree)"


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass
class VgpCrawlOptions:
    modules: Set[str] = field(default_factory=lambda: set(DEFAULT_MODULES))
    skip_unchanged: bool = True
    fallback_legacy_pha_he: bool = True
    sync_pipeline: bool = True
    attach_documents: bool = True
    force_documents: bool = False
    delay_seconds: float = 0.2
    timeout_seconds: float = 25.0


class VgpCrawlService:
    def __init__(
        self,
        *,
        db: Session,
        storage: Optional[ObjectStorage] = None,
        get_tree: Optional[Callable[[str], dict]] = None,
    ) -> None:
        self.db = db
        self.storage = storage
        self.get_tree = get_tree
        self.repository = VgpCrawlRepository(db)

    def crawl_range(
        self,
        *,
        start_id: int,
        end_id: int,
        options: Optional[VgpCrawlOptions] = None,
    ) -> Dict[str, Any]:
        opts = options or VgpCrawlOptions()
        summary: Dict[str, Any] = {
            "crawl_version": "v2",
            "start_id": start_id,
            "end_id": end_id,
            "upserted": [],
            "skipped_unchanged": [],
            "skipped_empty": [],
            "errors": [],
            "documents_attached": [],
            "documents_skipped": [],
            "document_errors": [],
        }

        headers = {"User-Agent": USER_AGENT}
        with httpx.Client(headers=headers, follow_redirects=True, timeout=opts.timeout_seconds) as client:
            for tree_id in range(start_id, end_id + 1):
                try:
                    result = self.crawl_one(client, tree_id=tree_id, options=opts)
                    status = result.get("status")
                    if status == "upserted":
                        summary["upserted"].append(result)
                    elif status == "skipped_unchanged":
                        summary["skipped_unchanged"].append(result)
                    elif status == "skipped_empty":
                        summary["skipped_empty"].append(result)
                    else:
                        summary["errors"].append(result)
                except Exception as exc:
                    summary["errors"].append(
                        {
                            "tree_id": tree_id,
                            "family_tree_id": store_id(tree_id),
                            "status": "error",
                            "error": str(exc),
                        }
                    )

                if opts.delay_seconds > 0 and tree_id < end_id:
                    time.sleep(opts.delay_seconds)

        return summary

    def crawl_one(
        self,
        client: httpx.Client,
        *,
        tree_id: int,
        options: VgpCrawlOptions,
    ) -> Dict[str, Any]:
        family_tree_id = store_id(tree_id)
        modules = {item.lower() for item in options.modules}

        metadata: Dict[str, Any] = {"tree_id": tree_id}
        pha_ky_text: Optional[str] = None
        nodes: List[Dict[str, Any]] = []
        relationships: List[Dict[str, Any]] = []
        parser_modes: Dict[str, str] = {}
        image_items: List[Dict[str, str]] = []
        urls: Dict[str, str] = {}

        if "giapha" in modules:
            giapha_response = client.get(giapha_url(tree_id))
            urls["giapha"] = str(giapha_response.url)
            if giapha_response.status_code >= 400:
                raise RuntimeError(f"giapha HTTP {giapha_response.status_code}")
            metadata = parse_giapha(giapha_response.text, tree_id=tree_id)
            parser_modes["giapha"] = "modern_section"

        if "pha_ky" in modules:
            pha_ky_response = client.get(pha_ky_url(tree_id))
            urls["pha_ky"] = str(pha_ky_response.url)
            if pha_ky_response.status_code >= 400:
                raise RuntimeError(f"pha_ky HTTP {pha_ky_response.status_code}")
            pha_ky_text = parse_pha_ky_text(pha_ky_response.text)
            parser_modes["pha_ky"] = "html_prose" if pha_ky_text else "empty"

        if "pha_he" in modules:
            pha_he_response = client.get(pha_he_url(tree_id))
            urls["pha_he"] = str(pha_he_response.url)
            html = pha_he_response.text if pha_he_response.status_code < 400 else ""
            nodes, relationships, pha_he_mode = parse_pha_he(html, tree_id=tree_id)

            if not nodes and options.fallback_legacy_pha_he:
                legacy_response = client.get(pha_he_legacy_url(tree_id))
                urls["pha_he_legacy"] = str(legacy_response.url)
                if legacy_response.status_code < 400:
                    nodes, relationships, pha_he_mode = parse_pha_he(legacy_response.text, tree_id=tree_id)

            parser_modes["pha_he"] = pha_he_mode

        if "images" in modules:
            image_response = client.get(hinh_anh_url(tree_id))
            urls["hinh_anh"] = str(image_response.url)
            if image_response.status_code < 400:
                image_items = parse_images(image_response.text, base_url=str(image_response.url))
            parser_modes["images"] = "none" if not image_items else "html_img"

        if not nodes and "pha_he" in modules:
            return {
                "tree_id": tree_id,
                "family_tree_id": family_tree_id,
                "status": "skipped_empty",
                "reason": "no_nodes",
            }

        pha_ky_hash = hash_text(pha_ky_text) if pha_ky_text else None
        content_hash = compute_vgp_content_hash(metadata=metadata, nodes=nodes, pha_ky_text=pha_ky_text)

        if options.skip_unchanged:
            existing_hash = self.repository.get_content_hash(family_tree_id)
            if existing_hash == content_hash:
                return {
                    "tree_id": tree_id,
                    "family_tree_id": family_tree_id,
                    "status": "skipped_unchanged",
                    "content_hash": content_hash,
                }

        lineage_name = metadata.get("lineage_name") or f"VietnamGiaPha tree {tree_id}"
        location = metadata.get("location")
        stats_bits = []
        for key, label in (
            ("generation_count", "đời"),
            ("family_count", "gia đình"),
            ("people_count", "người"),
        ):
            value = metadata.get(key)
            if isinstance(value, int):
                stats_bits.append(f"{value} {label}")
        description_parts = [part for part in [location, ", ".join(stats_bits)] if part]
        description = " | ".join(description_parts) if description_parts else None

        manifest = {
            "crawl_version": "v2",
            "fetched_at": _now_iso(),
            "urls": urls,
            "parser_modes": parser_modes,
            "stats": {
                "generations": metadata.get("generation_count"),
                "families": metadata.get("family_count"),
                "people": metadata.get("people_count"),
                "node_count": len(nodes),
                "relationship_count": len(relationships),
                "image_count": len(image_items),
            },
        }

        nodes_hash = self.repository.compute_nodes_hash_from_raw(nodes)
        has_documents = bool(pha_ky_text) or bool(image_items)

        upsert_result = self.repository.upsert_tree_and_crawl(
            family_tree_id=family_tree_id,
            tree_id=tree_id,
            name=str(lineage_name),
            description=description,
            external_url=urls.get("giapha") or giapha_url(tree_id),
            raw_nodes=nodes,
            metadata=metadata,
            manifest=manifest,
            content_hash=content_hash,
            nodes_hash=nodes_hash,
            pha_ky_hash=pha_ky_hash,
            has_source_document=has_documents,
        )

        document_results: Dict[str, Any] = {}
        if options.attach_documents and self.storage is not None and self.get_tree is not None:
            document_results = self._attach_documents(
                family_tree_id=family_tree_id,
                lineage_name=str(lineage_name),
                pha_ky_text=pha_ky_text,
                image_items=image_items,
                client=client,
                force=options.force_documents,
            )

        if options.sync_pipeline and self.get_tree is not None:
            pipeline = PipelineService(
                self.db,
                get_tree=self.get_tree,
                storage=self.storage,
            )
            pipeline.sync_from_tree_state(family_tree_id)

        self.db.flush()

        return {
            "tree_id": tree_id,
            "family_tree_id": family_tree_id,
            "status": "upserted",
            "node_count": upsert_result["node_count"],
            "content_hash": content_hash,
            "parser_modes": parser_modes,
            "documents": document_results,
        }

    def _attach_documents(
        self,
        *,
        family_tree_id: str,
        lineage_name: str,
        pha_ky_text: Optional[str],
        image_items: List[Dict[str, str]],
        client: httpx.Client,
        force: bool,
    ) -> Dict[str, Any]:
        service = DocumentService(self.db, self.storage, get_tree=self.get_tree)
        results: Dict[str, Any] = {}

        if pha_ky_text:
            results["pha_ky"] = attach_vgp_pha_ky_document(
                service=service,
                family_tree_id=family_tree_id,
                lineage_name=lineage_name,
                text_content=pha_ky_text,
                force=force,
            )

        if image_items:
            downloaded: List[tuple[str, bytes, str]] = []
            for item in image_items:
                response = client.get(item["url"])
                if response.status_code >= 400:
                    continue
                content_type = response.headers.get("content-type") or mimetypes.guess_type(item["filename"])[0]
                mime = content_type.split(";", 1)[0].strip() if content_type else "application/octet-stream"
                if not mime.startswith("image/"):
                    continue
                downloaded.append((item["filename"], response.content, mime))

            if downloaded:
                results["images"] = attach_vgp_images_document(
                    service=service,
                    family_tree_id=family_tree_id,
                    lineage_name=lineage_name,
                    files=downloaded,
                    force=force,
                )

        return results
