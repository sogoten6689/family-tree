from __future__ import annotations

import argparse
import hashlib
import json
import re
import time
from datetime import datetime, timezone
from html import unescape
from pathlib import Path
from typing import Any, Dict, List, Literal, Optional

import httpx

BASE_URL = "https://lib.nomfoundation.org"
VOLUME_URL_TEMPLATE = BASE_URL + "/collection/{collection_id}/volume/{volume_id}/"
PAGE_URL_TEMPLATE = BASE_URL + "/collection/{collection_id}/volume/{volume_id}/page/{page}/"
SITE_MEDIA_IMAGE_RE = re.compile(
    r"/site_media/nom/(.+?)/(large|jpeg)/([^/]+)-(\d+)\.jpg",
    re.IGNORECASE,
)
CATALOG_CODE_RE = re.compile(r"^(TNVNPF|NLVNPF)-(\d+)$", re.IGNORECASE)
ImageVariant = Literal["large", "jpeg"]


def extract_media_image_template(html: str) -> tuple[Optional[str], Optional[str]]:
    """Return (media_rel_path, file_prefix) from the first site_media image in HTML."""
    match = SITE_MEDIA_IMAGE_RE.search(html)
    if not match:
        return None, None
    return match.group(1), match.group(3)


def _media_candidates_from_catalog_code(catalog_code: str) -> List[tuple[str, str]]:
    catalog_match = CATALOG_CODE_RE.match(catalog_code.replace(" ", ""))
    if not catalog_match:
        return []

    series = catalog_match.group(1).upper()
    number = catalog_match.group(2)
    if series == "TNVNPF":
        slug = f"tnvnpf-{number}"
        return [(f"tnvnpf/{slug}", slug), (slug, slug)]
    slug = f"nlvnpf-{number}"
    return [(slug, slug)]


def _clean_html_text(value: str) -> str:
    value = re.sub(r"<[^>]+>", " ", value)
    value = unescape(value)
    value = value.replace("\xa0", " ")
    value = re.sub(r"\s+", " ", value)
    return value.strip()


def _split_title(title: str) -> tuple[Optional[str], Optional[str]]:
    cleaned = title.strip()
    for sep in ("|", "•", " - "):
        if sep in cleaned:
            parts = [part.strip("[] ") for part in cleaned.split(sep, 1)]
            if len(parts) == 2 and parts[0] and parts[1]:
                return parts[0], parts[1]
    return cleaned or None, None


def _parse_definition_list(html: str) -> Dict[str, str]:
    fields: Dict[str, str] = {}
    for match in re.finditer(r"<dt>([^<]+)</dt>\s*<dd>(.*?)</dd>", html, flags=re.IGNORECASE | re.DOTALL):
        key = _clean_html_text(match.group(1))
        value = _clean_html_text(match.group(2))
        if key:
            fields[key] = value
    return fields


def _parse_heading_codes(html: str) -> List[str]:
    return [_clean_html_text(code) for code in re.findall(r"<h2>(.*?)</h2>", html, flags=re.IGNORECASE | re.DOTALL)]


def extract_catalog_slug(html: str) -> Optional[str]:
    _, file_prefix = extract_media_image_template(html)
    if file_prefix:
        return file_prefix.lower()

    for code in _parse_heading_codes(html):
        catalog_match = CATALOG_CODE_RE.match(code.replace(" ", ""))
        if not catalog_match:
            continue
        prefix = "tnvnpf" if catalog_match.group(1).upper() == "TNVNPF" else "nlvnpf"
        return f"{prefix}-{catalog_match.group(2)}"
    return None


def _parse_page_count(html: str, fields: Dict[str, str]) -> Optional[int]:
    pages_value = fields.get("Pages", "").strip()
    if pages_value.isdigit():
        return int(pages_value)

    for pattern in (
        r"Page\s+\d+\s+of\s+(\d+)",
        r"(\d+)\s*pages?",
        r"Số trang[:\s]*(\d+)",
    ):
        match = re.search(pattern, html, flags=re.IGNORECASE)
        if match:
            return int(match.group(1))
    return None


def build_page_image_url(
    *,
    media_rel: str,
    file_prefix: str,
    page: int,
    variant: ImageVariant = "large",
) -> str:
    return f"{BASE_URL}/site_media/nom/{media_rel}/{variant}/{file_prefix}-{page:03d}.jpg"


def resolve_page_image_urls(
    metadata: Dict[str, Any],
    *,
    image_variant: ImageVariant = "large",
    max_pages: int = 100,
    page_start: int = 1,
    page_end: Optional[int] = None,
) -> List[str]:
    media_rel = metadata.get("media_rel")
    file_prefix = metadata.get("file_prefix") or metadata.get("catalog_slug")
    page_count = metadata.get("page_count")
    if not media_rel or not file_prefix:
        return []

    if not isinstance(page_count, int) or page_count <= 0:
        page_count = max_pages
    else:
        page_count = min(page_count, max_pages)

    start = max(1, int(page_start))
    end = int(page_end) if page_end is not None else page_count
    end = min(end, page_count)
    if start > end:
        return []

    return [
        build_page_image_url(
            media_rel=media_rel,
            file_prefix=file_prefix,
            page=page,
            variant=image_variant,
        )
        for page in range(start, end + 1)
    ]


def parse_volume_metadata(html: str, *, collection_id: int, volume_id: int) -> Dict[str, Any]:
    title_match = re.search(r"<title>(.*?)</title>", html, flags=re.IGNORECASE | re.DOTALL)
    raw_title = _clean_html_text(title_match.group(1)) if title_match else f"Volume {volume_id}"
    title_han, title_vn = _split_title(raw_title)

    h1_titles = [_clean_html_text(item) for item in re.findall(r"<h1[^>]*>(.*?)</h1>", html, flags=re.IGNORECASE | re.DOTALL)]
    if len(h1_titles) >= 2:
        title_han = h1_titles[0].strip("[] ")
        title_vn = h1_titles[1].strip("[] ")
    elif len(h1_titles) == 1 and not title_han:
        title_han = h1_titles[0].strip("[] ")

    fields = _parse_definition_list(html)
    heading_codes = _parse_heading_codes(html)
    catalog_code = next((code for code in heading_codes if CATALOG_CODE_RE.match(code.replace(" ", ""))), None)
    local_code = next((code for code in heading_codes if code and not CATALOG_CODE_RE.match(code.replace(" ", ""))), None)
    catalog_slug = extract_catalog_slug(html)
    media_rel, file_prefix = extract_media_image_template(html)
    if not media_rel and catalog_code:
        for candidate_rel, candidate_prefix in _media_candidates_from_catalog_code(catalog_code):
            media_rel = candidate_rel
            file_prefix = candidate_prefix
            break
    page_count = _parse_page_count(html, fields)

    return {
        "collection_id": collection_id,
        "volume_id": volume_id,
        "url": VOLUME_URL_TEMPLATE.format(collection_id=collection_id, volume_id=volume_id),
        "title": raw_title,
        "title_han": title_han,
        "title_vn": title_vn,
        "catalog_code": catalog_code,
        "local_code": local_code,
        "catalog_slug": catalog_slug,
        "media_rel": media_rel,
        "file_prefix": file_prefix,
        "page_count": page_count,
        "fields": fields,
        "fetched_at": datetime.now(timezone.utc).isoformat(),
    }


def _fetch_viewer_page_info(
    client: httpx.Client,
    *,
    collection_id: int,
    volume_id: int,
    page: int = 1,
) -> tuple[Optional[str], Optional[int]]:
    response = client.get(PAGE_URL_TEMPLATE.format(collection_id=collection_id, volume_id=volume_id, page=page))
    response.raise_for_status()
    html = response.text
    slug = extract_catalog_slug(html)
    page_count = _parse_page_count(html, _parse_definition_list(html))
    return slug, page_count


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _download_image(
    client: httpx.Client,
    *,
    image_url: str,
    target: Path,
    fallback_variant: Optional[ImageVariant] = None,
) -> tuple[str, int]:
    response = client.get(image_url)
    if response.status_code == 404 and fallback_variant and "/large/" in image_url:
        image_url = image_url.replace("/large/", f"/{fallback_variant}/")
        response = client.get(image_url)
    response.raise_for_status()
    target.write_bytes(response.content)
    return image_url, len(response.content)


def run(
    *,
    collection_id: int,
    volume_id: int,
    output_dir: Path,
    delay_seconds: float = 0.3,
    max_pages: int = 100,
    image_variant: ImageVariant = "large",
    page_start: int = 1,
    page_end: Optional[int] = None,
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
        "page_start": page_start,
        "page_end": page_end,
        "downloaded_pages": [],
        "skipped_pages": [],
        "errors": [],
    }

    with httpx.Client(follow_redirects=True, headers=headers, timeout=120.0) as client:
        volume_url = VOLUME_URL_TEMPLATE.format(collection_id=collection_id, volume_id=volume_id)
        response = client.get(volume_url)
        response.raise_for_status()
        metadata = parse_volume_metadata(
            response.text,
            collection_id=collection_id,
            volume_id=volume_id,
        )

        if not metadata.get("catalog_slug") or not metadata.get("page_count") or not metadata.get("media_rel"):
            viewer_slug, viewer_page_count = _fetch_viewer_page_info(
                client,
                collection_id=collection_id,
                volume_id=volume_id,
                page=1,
            )
            if viewer_slug and not metadata.get("catalog_slug"):
                metadata["catalog_slug"] = viewer_slug
            if viewer_page_count and not metadata.get("page_count"):
                metadata["page_count"] = viewer_page_count
            if not metadata.get("media_rel"):
                viewer_response = client.get(
                    PAGE_URL_TEMPLATE.format(collection_id=collection_id, volume_id=volume_id, page=1)
                )
                viewer_response.raise_for_status()
                media_rel, file_prefix = extract_media_image_template(viewer_response.text)
                if media_rel:
                    metadata["media_rel"] = media_rel
                if file_prefix and not metadata.get("file_prefix"):
                    metadata["file_prefix"] = file_prefix

        metadata["image_variant"] = image_variant
        page_urls = resolve_page_image_urls(
            metadata,
            image_variant=image_variant,
            max_pages=max_pages,
            page_start=page_start,
            page_end=page_end,
        )
        metadata["page_start"] = page_start
        metadata["page_end"] = page_end or metadata.get("page_count")
        metadata["page_urls"] = page_urls

        metadata_path = volume_dir / "metadata.json"
        metadata_path.write_text(json.dumps(metadata, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

        manifest_pages: List[Dict[str, Any]] = []
        for index, image_url in enumerate(page_urls, start=page_start):
            file_name = f"{index:03d}.jpg"
            target = pages_dir / file_name
            if target.exists() and target.stat().st_size > 0:
                manifest_pages.append(
                    {
                        "page": index,
                        "file": file_name,
                        "source_url": image_url,
                        "size": target.stat().st_size,
                        "sha256": _sha256_file(target),
                        "skipped": True,
                    }
                )
                summary["skipped_pages"].append(file_name)
                continue
            try:
                source_url, size = _download_image(
                    client,
                    image_url=image_url,
                    target=target,
                    fallback_variant="jpeg" if image_variant == "large" else None,
                )
                manifest_pages.append(
                    {
                        "page": index,
                        "file": file_name,
                        "source_url": source_url,
                        "size": size,
                        "sha256": _sha256_file(target),
                        "skipped": False,
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
            "catalog_slug": metadata.get("catalog_slug"),
            "image_variant": image_variant,
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
        "title": metadata.get("title_vn") or metadata.get("title"),
        "title_han": metadata.get("title_han"),
        "catalog_code": metadata.get("catalog_code"),
        "catalog_slug": metadata.get("catalog_slug"),
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
            "title": metadata.get("title_vn") or metadata.get("title"),
            "catalog_slug": metadata.get("catalog_slug"),
            "metadata_path": str(metadata_path),
            "manifest_path": str(volume_dir / "manifest.json"),
            "page_count": len(manifest_pages),
            "image_variant": image_variant,
        }
    )
    summary_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return summary


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Fetch Nom Foundation volume metadata and page images")
    parser.add_argument("--collection", type=int, default=2, help="Nom collection id (default: 2)")
    parser.add_argument("--volume", type=int, required=True, help="Nom volume id, e.g. 1255, 1256, 208")
    parser.add_argument("--output-dir", type=Path, default=Path("data/nomfoundation"))
    parser.add_argument("--delay-seconds", type=float, default=0.3)
    parser.add_argument("--max-pages", type=int, default=100)
    parser.add_argument("--page-start", type=int, default=1)
    parser.add_argument("--page-end", type=int, default=None)
    parser.add_argument(
        "--image-variant",
        choices=("large", "jpeg"),
        default="large",
        help="Image quality: large (~full scan) or jpeg (thumbnail)",
    )
    return parser


def main() -> None:
    args = build_parser().parse_args()
    summary = run(
        collection_id=args.collection,
        volume_id=args.volume,
        output_dir=args.output_dir,
        delay_seconds=args.delay_seconds,
        max_pages=args.max_pages,
        image_variant=args.image_variant,
        page_start=args.page_start,
        page_end=args.page_end,
    )
    print(
        f"Done volume={args.volume} ({summary.get('catalog_slug')}): "
        f"downloaded={len(summary.get('downloaded_pages', []))}, "
        f"skipped={len(summary.get('skipped_pages', []))}, "
        f"errors={len(summary.get('errors', []))}"
    )


if __name__ == "__main__":
    main()
