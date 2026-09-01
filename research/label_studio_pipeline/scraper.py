"""Web scraper for vietnamgiapha.com genealogy pages."""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass
from html import unescape
from typing import Optional
from urllib.parse import urljoin, urlparse

import requests
from bs4 import BeautifulSoup, Comment, NavigableString, Tag

logger = logging.getLogger(__name__)

DEFAULT_USER_AGENT = "family-tree-label-studio-pipeline/0.1 (+research)"
MIN_PROSE_CHARS = 400
NOISE_TAGS = ("script", "style", "noscript", "iframe", "svg")
SKIP_SECTION_HEADINGS = frozenset(
    {
        "tổng quan gia phả",
        "thông tin người quản lý gia phả",
        "các ngày lễ giỗ",
    }
)


@dataclass(frozen=True)
class ScrapeResult:
    """Structured output from a scrape run."""

    url: str
    title: str
    text: str
    tree_id: Optional[int] = None


def _normalize_whitespace(text: str) -> str:
    text = unescape(text)
    text = text.replace("\xa0", " ").replace("\u200b", "").replace("\ufeff", "")
    text = re.sub(r"[ \t]+\n", "\n", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    text = re.sub(r"[ \t]{2,}", " ", text)
    return text.strip()


def _tag_text(tag: Tag) -> str:
    parts: list[str] = []
    for child in tag.descendants:
        if isinstance(child, Comment):
            continue
        if isinstance(child, NavigableString):
            chunk = str(child)
            if chunk.strip():
                parts.append(chunk)
    return _normalize_whitespace(" ".join(parts))


def _extract_tree_id(url: str) -> Optional[int]:
    match = re.search(r"/(?:XemGiaPha|XemPhaKy|XemThuyTo|XemPhaHe)/(\d+)/", url)
    if not match:
        return None
    return int(match.group(1))


def _pha_ky_url(tree_id: int) -> str:
    return f"https://vietnamgiapha.com/XemPhaKy/{tree_id}/pha_ky_gia_su.html"


def _remove_noise(root: Tag) -> None:
    for tag_name in NOISE_TAGS:
        for node in root.find_all(tag_name):
            node.decompose()
    for node in root.find_all(["nav", "header", "footer"]):
        node.decompose()
    for node in root.find_all(class_=re.compile(r"\b(tabs|cta|footer|site-header|legal-nav)\b")):
        node.decompose()


def _extract_legacy_content(soup: BeautifulSoup) -> str:
    legacy = soup.select_one(".legacy-content")
    if legacy is None:
        return ""
    _remove_noise(legacy)
    return _normalize_whitespace(legacy.get_text(separator="\n", strip=True))


def _extract_section_prose(soup: BeautifulSoup) -> str:
    main = soup.find("main")
    if main is None:
        return ""

    blocks: list[str] = []
    for section in main.find_all("section", class_="section"):
        heading = section.find(["h2", "h3"])
        heading_text = heading.get_text(strip=True).lower() if heading else ""
        if heading_text in SKIP_SECTION_HEADINGS:
            continue

        clone = BeautifulSoup(str(section), "html.parser")
        _remove_noise(clone)
        if clone.select_one(".legacy-content"):
            continue

        body = _normalize_whitespace(clone.get_text(separator="\n", strip=True))
        if body:
            blocks.append(body)

    return _normalize_whitespace("\n\n".join(blocks))


def _extract_title(soup: BeautifulSoup) -> str:
    if soup.title and soup.title.string:
        title = soup.title.string.strip()
        title = re.sub(r"\s*\|\s*Việt Nam Gia Phả\s*$", "", title, flags=re.IGNORECASE)
        return title
    header = soup.select_one(".site-header h1")
    if header:
        return header.get_text(strip=True)
    return ""


def _fetch_html(url: str, timeout: float) -> str:
    logger.info("Fetching URL: %s", url)
    response = requests.get(
        url,
        timeout=timeout,
        headers={"User-Agent": DEFAULT_USER_AGENT},
    )
    response.raise_for_status()
    response.encoding = response.apparent_encoding or "utf-8"
    logger.info("Fetched %d bytes (HTTP %s)", len(response.content), response.status_code)
    return response.text


def _compose_text(*parts: str) -> str:
    seen: set[str] = set()
    ordered: list[str] = []
    for part in parts:
        cleaned = _normalize_whitespace(part)
        if not cleaned or cleaned in seen:
            continue
        seen.add(cleaned)
        ordered.append(cleaned)
    return _normalize_whitespace("\n\n".join(ordered))


def scrape_genealogy_text(
    url: str,
    *,
    timeout: float = 30.0,
    follow_pha_ky: bool = True,
) -> ScrapeResult:
    """
    Download a vietnamgiapha.com page and extract genealogy prose.

    For overview pages (``XemGiaPha/.../giapha.html``) with little prose, optionally
    follows the Phả ký tab when ``follow_pha_ky=True``.
    """
    html = _fetch_html(url, timeout=timeout)
    soup = BeautifulSoup(html, "html.parser")
    title = _extract_title(soup)
    tree_id = _extract_tree_id(url)

    legacy_text = _extract_legacy_content(soup)
    section_text = _extract_section_prose(soup)
    text = _compose_text(section_text, legacy_text)

    if follow_pha_ky and len(text) < MIN_PROSE_CHARS and tree_id is not None:
        pha_ky_url = _pha_ky_url(tree_id)
        if urlparse(pha_ky_url).path != urlparse(url).path:
            logger.info(
                "Prose too short (%d chars); fetching Phả ký fallback: %s",
                len(text),
                pha_ky_url,
            )
            pha_ky_html = _fetch_html(pha_ky_url, timeout=timeout)
            pha_ky_soup = BeautifulSoup(pha_ky_html, "html.parser")
            pha_ky_legacy = _extract_legacy_content(pha_ky_soup)
            if pha_ky_legacy:
                text = _compose_text(text, pha_ky_legacy)
                url = pha_ky_url
                if not title:
                    title = _extract_title(pha_ky_soup)

    if not text:
        raise ValueError(f"No genealogy prose extracted from {url}")

    logger.info("Extracted %d characters of prose from %s", len(text), url)
    return ScrapeResult(url=url, title=title, text=text, tree_id=tree_id)


def resolve_url(url: str) -> str:
    """Normalize relative vietnamgiapha paths to absolute URLs."""
    if url.startswith("http://") or url.startswith("https://"):
        return url
    base = "https://vietnamgiapha.com/"
    return urljoin(base, url.lstrip("/"))
