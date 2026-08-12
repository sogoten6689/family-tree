"""Download vietnamgiapha.com image gallery pages."""

from __future__ import annotations

import logging
import re
from pathlib import Path
from urllib.parse import urljoin

import requests

from label_studio_pipeline.html_utils import DEFAULT_USER_AGENT, fetch_html_optional
from label_studio_pipeline.vgp_urls import hinh_anh_url

logger = logging.getLogger(__name__)

_IMG_PATTERN = re.compile(r"""<img[^>]+src=["'](?P<src>[^"']+)["']""", re.IGNORECASE)
_SKIP_IMAGE_FRAGMENTS = (
    "logo",
    "banner",
    "icon",
    "avatar",
    "spacer",
    "clear.png",
    "green-bar",
    "mag+",
)


def parse_image_links(html: str, *, base_url: str) -> list[dict[str, str]]:
    images: list[dict[str, str]] = []
    seen: set[str] = set()

    for match in _IMG_PATTERN.finditer(html):
        src = match.group("src").strip()
        if not src or src.startswith("data:"):
            continue
        lowered = src.lower()
        if any(fragment in lowered for fragment in _SKIP_IMAGE_FRAGMENTS):
            continue
        absolute = urljoin(base_url, src)
        if absolute in seen:
            continue
        seen.add(absolute)
        filename = absolute.rsplit("/", 1)[-1].split("?", 1)[0] or "image.jpg"
        images.append({"url": absolute, "filename": filename})

    return images


def _is_spa_shell(html: str) -> bool:
    lowered = html.lower()
    return "data-beasties-container" in lowered or "<app-root" in lowered


def download_tree_images(
    tree_id: int,
    output_dir: Path,
    *,
    timeout: float = 30.0,
) -> dict:
    """Fetch hinh_anh.html and save linked images under output_dir/images/."""
    url = hinh_anh_url(tree_id)
    html, status = fetch_html_optional(url, timeout=timeout)
    if not html:
        return {
            "tree_id": tree_id,
            "status": "unavailable",
            "source_url": url,
            "http_status": status,
            "image_count": 0,
            "files": [],
        }

    links = parse_image_links(html, base_url=url)
    if not links:
        status = "spa_shell" if _is_spa_shell(html) else "empty"
        return {
            "tree_id": tree_id,
            "status": status,
            "source_url": url,
            "http_status": status,
            "image_count": 0,
            "files": [],
            "note": (
                "vietnamgiapha.com trả về SPA shell — không còn thẻ <img> tĩnh trên hinh_anh.html"
                if status == "spa_shell"
                else None
            ),
        }

    images_dir = output_dir / "images"
    images_dir.mkdir(parents=True, exist_ok=True)
    saved: list[str] = []

    for index, item in enumerate(links, start=1):
        image_url = item["url"]
        filename = item["filename"]
        if not re.search(r"\.(jpe?g|png|gif|webp)$", filename, re.IGNORECASE):
            ext = ".jpg"
            if ".png" in image_url.lower():
                ext = ".png"
            filename = f"{index:03d}{ext}"

        dest = images_dir / filename
        try:
            response = requests.get(
                image_url,
                timeout=timeout,
                headers={"User-Agent": DEFAULT_USER_AGENT},
            )
        except requests.RequestException as exc:
            logger.warning("tree_id=%s image error url=%s err=%s", tree_id, image_url, exc)
            continue
        if response.status_code != 200:
            logger.warning("tree_id=%s image skip status=%s url=%s", tree_id, response.status_code, image_url)
            continue
        dest.write_bytes(response.content)
        saved.append(filename)

    return {
        "tree_id": tree_id,
        "status": "ok" if saved else "empty",
        "source_url": url,
        "http_status": status,
        "image_count": len(saved),
        "files": saved,
    }
