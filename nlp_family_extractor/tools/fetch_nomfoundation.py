from __future__ import annotations

import argparse
import json
import re
import time
from datetime import datetime, timezone
from html import unescape
from pathlib import Path
from typing import Any, Dict, List, Optional
from urllib.parse import urljoin

import httpx

BASE_URL = "https://lib.nomfoundation.org"
VOLUME_URL_TEMPLATE = BASE_URL + "/collection/{collection_id}/volume/{volume_id}/"


def _clean_html_text(value: str) -> str:
    value = re.sub(r"<[^>]+>", " ", value)
    value = unescape(value)
    value = value.replace("\xa0", " ")
    value = re.sub(r"\s+", " ", value)
    return value.strip()


def parse_volume_metadata(html: str, *, collection_id: int, volume_id: int) -> Dict[str, Any]:
    title_match = re.search(r"<title>(.*?)</title>", html, flags=re.IGNORECASE | re.DOTALL)
    title = _clean_html_text(title_match.group(1)) if title_match else f"Volume {volume_id}"

    page_count = None
    for pattern in (
        r"(\d+)\s*pages?",
        r"Số trang[:\s]*(\d+)",
        r"pageCount[\"']?\s*[:=]\s*(\d+)",
    ):
        match = re.search(pattern, html, flags=re.IGNORECASE)
        if match:
            try:
                page_count = int(match.group(1))
                break
            except ValueError:
                continue

    image_urls = sorted(
        {
            urljoin(BASE_URL, href)
            for href in re.findall(r"""href=["']([^"']+\.(?:jpg|jpeg|png|webp))["']""", html, flags=re.IGNORECASE)
        }
    )

    iiif_urls = sorted(
        {
            urljoin(BASE_URL, href)
            for href in re.findall(r"""href=["']([^"']*iiif[^"']*)["']""", html, flags=re.IGNORECASE)
        }
    )

    return {
        "collection_id": collection_id,
        "volume_id": volume_id,
        "url": VOLUME_URL_TEMPLATE.format(collection_id=collection_id, volume_id=volume_id),
        "title": title,
        "page_count_hint": page_count,
        "image_urls": image_urls[:20],
        "iiif_urls": iiif_urls[:20],
        "fetched_at": datetime.now(timezone.utc).isoformat(),
    }


def discover_page_image_urls(
    client: httpx.Client,
    *,
    collection_id: int,
    volume_id: int,
    max_pages: int = 20,
) -> List[str]:
    """Best-effort discovery of per-page image URLs (requires spike validation per volume)."""
    candidates: List[str] = []
    patterns = [
        BASE_URL + "/collection/{collection_id}/volume/{volume_id}/page/{page}/",
        BASE_URL + "/collection/{collection_id}/volume/{volume_id}/image/{page}.jpg",
        BASE_URL + "/iiif/2/volume-{volume_id}/page-{page}/full/full/0/default.jpg",
    ]

    for page in range(1, max_pages + 1):
        for template in patterns:
            url = template.format(collection_id=collection_id, volume_id=volume_id, page=page)
            try:
                response = client.head(url, timeout=10.0)
            except Exception:
                continue
            if response.status_code == 200:
                content_type = response.headers.get("content-type", "")
                if "image" in content_type or url.endswith(".jpg"):
                    candidates.append(url)
                    break
    return candidates


def run(
    *,
    collection_id: int,
    volume_id: int,
    output_dir: Path,
    delay_seconds: float = 0.3,
    discover_pages: bool = True,
    max_pages: int = 20,
) -> Dict[str, Any]:
    output_dir.mkdir(parents=True, exist_ok=True)
    volume_dir = output_dir / "volumes" / str(volume_id)
    volume_dir.mkdir(parents=True, exist_ok=True)
    pages_dir = volume_dir / "pages"
    pages_dir.mkdir(parents=True, exist_ok=True)

    headers = {"User-Agent": "family-tree-research-tool/1.0 (+https://github.com)"}
    summary: Dict[str, Any] = {
        "collection_id": collection_id,
        "volume_id": volume_id,
        "downloaded_pages": [],
        "errors": [],
    }

    with httpx.Client(follow_redirects=True, headers=headers, timeout=30.0) as client:
        volume_url = VOLUME_URL_TEMPLATE.format(collection_id=collection_id, volume_id=volume_id)
        response = client.get(volume_url)
        response.raise_for_status()
        metadata = parse_volume_metadata(
            response.text,
            collection_id=collection_id,
            volume_id=volume_id,
        )

        page_urls = metadata.get("image_urls", [])
        if discover_pages and not page_urls:
            page_urls = discover_page_image_urls(
                client,
                collection_id=collection_id,
                volume_id=volume_id,
                max_pages=max_pages,
            )
        metadata["discovered_page_urls"] = page_urls

        metadata_path = volume_dir / "metadata.json"
        metadata_path.write_text(json.dumps(metadata, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

        manifest_pages: List[Dict[str, Any]] = []
        for index, image_url in enumerate(page_urls, start=1):
            file_name = f"{index:03d}.jpg"
            target = pages_dir / file_name
            if target.exists() and target.stat().st_size > 0:
                manifest_pages.append(
                    {
                        "page": index,
                        "file": file_name,
                        "source_url": image_url,
                        "skipped": True,
                    }
                )
                continue
            try:
                image_response = client.get(image_url)
                image_response.raise_for_status()
                target.write_bytes(image_response.content)
                manifest_pages.append(
                    {
                        "page": index,
                        "file": file_name,
                        "source_url": image_url,
                        "size": len(image_response.content),
                    }
                )
                summary["downloaded_pages"].append(file_name)
            except Exception as exc:
                summary["errors"].append({"page": index, "url": image_url, "error": str(exc)})
            if delay_seconds > 0:
                time.sleep(delay_seconds)

        manifest = {
            "collection_id": collection_id,
            "volume_id": volume_id,
            "downloaded_at": datetime.now(timezone.utc).isoformat(),
            "pages": manifest_pages,
        }
        (volume_dir / "manifest.json").write_text(
            json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )

    catalog_path = output_dir / "catalog.json"
    catalog: Dict[str, Any] = {"volumes": []}
    if catalog_path.exists():
        try:
            loaded = json.loads(catalog_path.read_text(encoding="utf-8"))
            if isinstance(loaded, dict) and isinstance(loaded.get("volumes"), list):
                catalog = loaded
        except (OSError, json.JSONDecodeError):
            pass

    entry = {
        "collection_id": collection_id,
        "volume_id": volume_id,
        "title": metadata.get("title"),
        "url": metadata.get("url"),
        "page_count": len(manifest_pages),
    }
    catalog["volumes"] = [
        item
        for item in catalog.get("volumes", [])
        if not (
            isinstance(item, dict)
            and item.get("collection_id") == collection_id
            and item.get("volume_id") == volume_id
        )
    ]
    catalog["volumes"].append(entry)
    catalog_path.write_text(json.dumps(catalog, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    summary_path = output_dir / "summary.json"
    summary.update(
        {
            "metadata_path": str(metadata_path),
            "manifest_path": str(volume_dir / "manifest.json"),
            "page_count": len(manifest_pages),
        }
    )
    summary_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return summary


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Fetch Nom Foundation volume metadata and page images")
    parser.add_argument("--collection", type=int, default=1)
    parser.add_argument("--volume", type=int, required=True)
    parser.add_argument("--output-dir", type=Path, default=Path("data/nomfoundation"))
    parser.add_argument("--delay-seconds", type=float, default=0.3)
    parser.add_argument("--max-pages", type=int, default=20)
    parser.add_argument("--no-discover-pages", action="store_true")
    return parser


def main() -> None:
    args = build_parser()
    summary = run(
        collection_id=args.collection,
        volume_id=args.volume,
        output_dir=args.output_dir,
        delay_seconds=args.delay_seconds,
        discover_pages=not args.no_discover_pages,
        max_pages=args.max_pages,
    )
    print(
        f"Done volume={args.volume}: "
        f"downloaded={len(summary.get('downloaded_pages', []))}, "
        f"errors={len(summary.get('errors', []))}"
    )


if __name__ == "__main__":
    main()
