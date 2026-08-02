"""Shared HTML fetch and text extraction helpers."""

from __future__ import annotations

import logging
import re
from html import unescape

import requests
from bs4 import BeautifulSoup, Comment, NavigableString, Tag

logger = logging.getLogger(__name__)

DEFAULT_USER_AGENT = "family-tree-label-studio-pipeline/0.1 (+research)"
NOISE_TAGS = ("script", "style", "noscript", "iframe", "svg")


def normalize_whitespace(text: str) -> str:
    text = unescape(text)
    text = text.replace("\xa0", " ").replace("\u200b", "").replace("\ufeff", "")
    text = re.sub(r"[ \t]+\n", "\n", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    text = re.sub(r"[ \t]{2,}", " ", text)
    return text.strip()


def fetch_html(url: str, *, timeout: float = 30.0) -> str:
    logger.debug("GET %s", url)
    response = requests.get(
        url,
        timeout=timeout,
        headers={"User-Agent": DEFAULT_USER_AGENT},
    )
    response.raise_for_status()
    response.encoding = response.apparent_encoding or "utf-8"
    return response.text


def fetch_html_optional(url: str, *, timeout: float = 30.0) -> tuple[str | None, int | None]:
    """Return (html, status_code). Does not raise on HTTP errors."""
    try:
        response = requests.get(
            url,
            timeout=timeout,
            headers={"User-Agent": DEFAULT_USER_AGENT},
        )
        status = response.status_code
        if status != 200:
            return None, status
        response.encoding = response.apparent_encoding or "utf-8"
        return response.text, status
    except requests.RequestException as exc:
        logger.debug("Request failed for %s: %s", url, exc)
        return None, None


def remove_noise(root: Tag) -> None:
    for tag_name in NOISE_TAGS:
        for node in root.find_all(tag_name):
            node.decompose()
    for node in root.find_all(["nav", "header", "footer"]):
        node.decompose()
    for node in root.find_all(class_=re.compile(r"\b(tabs|cta|footer|site-header|legal-nav)\b")):
        node.decompose()


def extract_title(soup: BeautifulSoup) -> str:
    if soup.title and soup.title.string:
        title = soup.title.string.strip()
        return re.sub(r"\s*\|\s*Việt Nam Gia Phả\s*$", "", title, flags=re.IGNORECASE)
    header = soup.select_one(".site-header h1")
    if header:
        return header.get_text(strip=True)
    return ""


def extract_lineage_name(soup: BeautifulSoup) -> str:
    header = soup.select_one(".site-header h1")
    if header:
        return normalize_whitespace(header.get_text())
    return ""


def extract_legacy_content(html: str) -> str:
    soup = BeautifulSoup(html, "html.parser")
    legacy = soup.select_one(".legacy-content")
    if legacy is None:
        return ""
    remove_noise(legacy)
    return normalize_whitespace(legacy.get_text(separator="\n", strip=True))


def extract_giapha_meta(html: str) -> dict[str, str | int | None]:
    """Parse overview fields from giapha.html."""
    soup = BeautifulSoup(html, "html.parser")
    meta: dict[str, str | int | None] = {
        "lineage_name": extract_lineage_name(soup) or None,
        "title": extract_title(soup) or None,
        "location": None,
        "person_count": None,
        "family_count": None,
        "generation_count": None,
    }

    for section in soup.find_all("section", class_="section"):
        heading = section.find("h2")
        heading_text = heading.get_text(strip=True).lower() if heading else ""
        body = normalize_whitespace(section.get_text(separator=" ", strip=True))

        if heading_text == "ở tại":
            meta["location"] = body.replace("Ở tại", "", 1).strip() or body
        elif heading_text == "tổng quan gia phả":
            person = re.search(r"(\d+)\s*Số người", body, flags=re.IGNORECASE)
            family = re.search(r"(\d+)\s*Số lượng gia đình", body, flags=re.IGNORECASE)
            generations = re.search(r"(\d+)\s*Số đời", body, flags=re.IGNORECASE)
            if person:
                meta["person_count"] = int(person.group(1))
            if family:
                meta["family_count"] = int(family.group(1))
            if generations:
                meta["generation_count"] = int(generations.group(1))

    return meta
