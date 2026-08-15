"""Filter and classify URLs from Firecrawl map results."""

from __future__ import annotations

import re
from urllib.parse import urlparse

from source_discovery.seeds import HANNOM_URL_KEYWORDS, QUOC_NGU_URL_KEYWORDS


def _normalize_url(url: str) -> str:
    return url.strip().rstrip("/")


def filter_urls(urls: list[str], track: str) -> list[str]:
    keywords = HANNOM_URL_KEYWORDS if track == "hannom" else QUOC_NGU_URL_KEYWORDS
    pattern = re.compile("|".join(re.escape(k) for k in keywords), re.IGNORECASE)
    seen: set[str] = set()
    filtered: list[str] = []
    for url in urls:
        normalized = _normalize_url(url)
        if normalized in seen:
            continue
        if pattern.search(url):
            seen.add(normalized)
            filtered.append(url)
    return filtered


def extract_links_from_map_response(response: object) -> list[str]:
    links: list = []

    if isinstance(response, dict):
        raw = response.get("links") or response.get("data") or []
        links = raw.get("links", raw) if isinstance(raw, dict) else raw
    elif hasattr(response, "links") and getattr(response, "links"):
        links = list(getattr(response, "links") or [])
    elif hasattr(response, "model_dump"):
        dumped = response.model_dump()
        raw = dumped.get("links") or dumped.get("data") or []
        links = raw.get("links", raw) if isinstance(raw, dict) else raw
    else:
        links = []

    urls: list[str] = []
    for item in links:
        if isinstance(item, str):
            urls.append(item)
            continue
        if isinstance(item, dict):
            url = item.get("url") or item.get("link")
            if url:
                urls.append(str(url))
            continue
        url = getattr(item, "url", None) or getattr(item, "link", None)
        if url:
            urls.append(str(url))
    return urls


def url_domain(url: str) -> str:
    return urlparse(url).netloc.lower()
