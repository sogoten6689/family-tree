"""Score scraped page samples for genealogy source feasibility."""

from __future__ import annotations

import re
from typing import Any

RELATION_CUE_PATTERN = re.compile(
    r"\b(con|hạ sinh|sinh|vợ|chồng|thê|phu|đời thứ|thế hệ|người con)\b",
    re.IGNORECASE,
)
GENEALOGY_TITLE_PATTERN = re.compile(
    r"(gia phả|tộc phả|phả ký|phả đồ|thế phả|tông phả|族譜|家譜)",
    re.IGNORECASE,
)
IMAGE_LINK_PATTERN = re.compile(
    r"(\.jpg|\.jpeg|\.png|\.pdf|/large/|/pages/|site_media/nom)",
    re.IGNORECASE,
)
HAN_NOM_PATTERN = re.compile(r"[\u4e00-\u9fff\u3400-\u4dbf]")
PAGE_COUNT_PATTERN = re.compile(r"\b(\d{1,4})\s*(trang|pages?)\b", re.IGNORECASE)
TREE_PATTERN = re.compile(
    r"(pha_he|pha-he|phả hệ|sơ đồ|cay_pha|genealogy|family.?tree|xemphaky|xemphehe)",
    re.IGNORECASE,
)


def _text_blob(scrape: dict[str, Any]) -> str:
    parts: list[str] = []
    for key in ("markdown", "html", "rawHtml", "content"):
        val = scrape.get(key)
        if isinstance(val, str):
            parts.append(val)
    metadata = scrape.get("metadata") or {}
    if isinstance(metadata, dict):
        for key in ("title", "description", "ogTitle", "ogDescription"):
            val = metadata.get(key)
            if isinstance(val, str):
                parts.append(val)
    links = scrape.get("links") or []
    if isinstance(links, list):
        parts.extend(str(x) for x in links[:200])
    return "\n".join(parts)


def _link_list(scrape: dict[str, Any]) -> list[str]:
    links = scrape.get("links") or []
    if not isinstance(links, list):
        return []
    out: list[str] = []
    for item in links:
        if isinstance(item, str):
            out.append(item)
        elif isinstance(item, dict):
            url = item.get("url") or item.get("href")
            if url:
                out.append(str(url))
    return out


def scrape_to_dict(response: object) -> dict[str, Any]:
    if isinstance(response, dict):
        data = response.get("data") if "data" in response else response
        return data if isinstance(data, dict) else {"raw": response}
    if hasattr(response, "model_dump"):
        dumped = response.model_dump()
        if isinstance(dumped.get("data"), dict):
            return dumped["data"]
        return dumped
    if hasattr(response, "__dict__"):
        return {k: v for k, v in response.__dict__.items() if not k.startswith("_")}
    return {"raw": str(response)}


def score_hannom(scrape: dict[str, Any], url: str) -> dict[str, Any]:
    text = _text_blob(scrape)
    links = _link_list(scrape)
    all_links_text = "\n".join(links)

    score = 0
    breakdown: dict[str, int] = {}

    image_hits = len(IMAGE_LINK_PATTERN.findall(all_links_text + "\n" + text))
    if image_hits >= 1:
        breakdown["image_links"] = 40
        score += 40
    elif IMAGE_LINK_PATTERN.search(url):
        breakdown["image_links"] = 20
        score += 20

    if GENEALOGY_TITLE_PATTERN.search(text) or GENEALOGY_TITLE_PATTERN.search(url):
        breakdown["genealogy_title"] = 25
        score += 25
    if HAN_NOM_PATTERN.search(text):
        breakdown["han_nom_text"] = 15
        score += 15
    if PAGE_COUNT_PATTERN.search(text):
        breakdown["page_metadata"] = 15
        score += 15
    if "/volume/" in url and "/page/" not in url:
        breakdown["volume_root"] = 5
        score += 5

    decision = "reject"
    if score >= 70:
        decision = "collect"
    elif score >= 45:
        decision = "pilot"

    return {
        "track": "hannom",
        "url": url,
        "score": score,
        "decision": decision,
        "breakdown": breakdown,
        "char_count": len(text),
        "image_link_hits": image_hits,
        "has_han_nom": bool(HAN_NOM_PATTERN.search(text)),
        "title_guess": (scrape.get("metadata") or {}).get("title"),
    }


def score_quoc_ngu(scrape: dict[str, Any], url: str) -> dict[str, Any]:
    text = _text_blob(scrape)
    links = _link_list(scrape)
    all_text = text + "\n" + "\n".join(links)

    score = 0
    breakdown: dict[str, int] = {}

    relation_hits = len(RELATION_CUE_PATTERN.findall(text))
    if relation_hits >= 5:
        breakdown["relation_cues"] = 30
        score += 30
    elif relation_hits >= 1:
        breakdown["relation_cues"] = 15
        score += 15

    if TREE_PATTERN.search(all_text) or TREE_PATTERN.search(url):
        breakdown["tree_links"] = 30
        score += 30

    prose_len = len(re.sub(r"\s+", " ", text).strip())
    if prose_len >= 200:
        breakdown["prose_length"] = 25
        score += 25
    elif prose_len >= 80:
        breakdown["prose_length"] = 10
        score += 10

    if re.search(r"\b(tỉnh|huyện|xã|quê|làng|tổ|dòng họ)\b", text, re.IGNORECASE):
        breakdown["location_metadata"] = 15
        score += 15

    decision = "reject"
    if score >= 70:
        decision = "collect"
    elif score >= 45:
        decision = "pilot"

    return {
        "track": "quoc_ngu",
        "url": url,
        "score": score,
        "decision": decision,
        "breakdown": breakdown,
        "char_count": prose_len,
        "relation_cue_hits": relation_hits,
        "title_guess": (scrape.get("metadata") or {}).get("title"),
    }


def score_scrape(track: str, scrape: dict[str, Any], url: str) -> dict[str, Any]:
    if track == "hannom":
        return score_hannom(scrape, url)
    return score_quoc_ngu(scrape, url)
