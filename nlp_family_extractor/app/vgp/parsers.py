from __future__ import annotations

import hashlib
import json
import re
from dataclasses import asdict
from html import unescape
from typing import Any, Dict, List, Optional, Tuple

from tools.fetch_vietnamgiapha import (
    NodeItem,
    infer_parent_relationships,
    parse_nodes as parse_legacy_nodes,
)

_LINK_PATTERN = re.compile(
    r'href=["\'][^"\']*/XemChiTietTungNguoi/\d+/(?P<node_id>\d+)/giapha\.html["\'][^>]*>'
    r"(?P<name>[^<]+)</a>",
    flags=re.IGNORECASE,
)
_GEN_ORDER_PATTERN = re.compile(r"<b>\s*(\d+)\.(\d+)\s*</b>", flags=re.IGNORECASE)
_SECTION_PATTERN = re.compile(
    r"<section[^>]*>\s*<h2>(?P<title>[^<]+)</h2>\s*(?P<body>.*?)</section>",
    flags=re.IGNORECASE | re.DOTALL,
)
_STAT_PATTERN = re.compile(
    r"<div\s+class=[\"']stat[\"'][^>]*>\s*<strong>(?P<value>[^<]+)</strong>\s*(?P<label>[^<]+)",
    flags=re.IGNORECASE | re.DOTALL,
)
_IMG_PATTERN = re.compile(
    r'<img[^>]+src=["\'](?P<src>[^"\']+)["\'][^>]*>',
    flags=re.IGNORECASE,
)
_SKIP_IMAGE_FRAGMENTS = (
    "favicon",
    "logo",
    "treeimg/",
    "mi.gif",
    "mid.gif",
    "/icons/",
)


def _clean_html_text(value: str) -> str:
    value = re.sub(r"<[^>]+>", " ", value)
    value = unescape(value)
    value = value.replace("\xa0", " ")
    value = re.sub(r"\s+", " ", value)
    return value.strip()


def _section_body(html: str, title: str) -> Optional[str]:
    for match in _SECTION_PATTERN.finditer(html):
        if _clean_html_text(match.group("title")).lower() == title.lower():
            body = match.group("body")
            paragraph = re.search(r"<p[^>]*>(.*?)</p>", body, flags=re.IGNORECASE | re.DOTALL)
            if paragraph:
                return _clean_html_text(paragraph.group(1))
            return _clean_html_text(body)
    return None


def _parse_int(value: str) -> Optional[int]:
    digits = re.sub(r"[^\d]", "", value)
    if not digits:
        return None
    try:
        return int(digits)
    except ValueError:
        return None


def detect_pha_he_mode(html: str) -> str:
    lowered = html.lower()
    if "javascript:o(" in lowered:
        return "legacy_js"
    if 'class="gt"' in lowered or "class='gt'" in lowered:
        return "modern_gt"
    if re.search(r"\d+\.\d+\s+", _clean_html_text(html)):
        return "flat_text"
    return "unknown"


def parse_giapha(html: str, *, tree_id: int) -> Dict[str, Any]:
    title_match = re.search(r"<h1[^>]*>(.*?)</h1>", html, flags=re.IGNORECASE | re.DOTALL)
    lineage_name = _clean_html_text(title_match.group(1)) if title_match else None

    if not lineage_name:
        og_match = re.search(
            r'<meta\s+property=["\']og:title["\']\s+content=["\']([^"\']+)["\']',
            html,
            flags=re.IGNORECASE,
        )
        if og_match:
            raw = _clean_html_text(og_match.group(1))
            lineage_name = re.sub(r"^Gia phả:\s*", "", raw, flags=re.IGNORECASE)
            lineage_name = re.sub(r"\s*\|\s*Việt Nam Gia Phả.*$", "", lineage_name, flags=re.IGNORECASE)

    location = _section_body(html, "Ở tại")
    manager_name = None
    manager_section = _section_body(html, "Thông tin người quản lý gia phả")
    if manager_section:
        manager_match = re.search(r"Người làm:\s*(.+)$", manager_section, flags=re.IGNORECASE)
        if manager_match:
            manager_name = manager_match.group(1).strip()

    generation_count = None
    family_count = None
    people_count = None

    stats_block = re.search(
        r"<h2>\s*Tổng quan gia phả\s*</h2>(.*?)</section>",
        html,
        flags=re.IGNORECASE | re.DOTALL,
    )
    if stats_block:
        for stat in _STAT_PATTERN.finditer(stats_block.group(1)):
            label = _clean_html_text(stat.group("label")).lower()
            value = _parse_int(stat.group("value"))
            if value is None:
                continue
            if "số đời" in label or "đời từ thủy tổ" in label:
                generation_count = value
            elif "gia đình" in label:
                family_count = value
            elif "số người" in label or "người trong gia phả" in label:
                people_count = value

    if people_count is None:
        desc_match = re.search(
            r'<meta\s+name=["\']description["\']\s+content=["\']([^"\']+)["\']',
            html,
            flags=re.IGNORECASE,
        )
        if desc_match:
            people_match = re.search(r"(\d+)\s+người", desc_match.group(1), flags=re.IGNORECASE)
            if people_match:
                people_count = int(people_match.group(1))
            family_match = re.search(r"(\d+)\s+gia đình", desc_match.group(1), flags=re.IGNORECASE)
            if family_match:
                family_count = int(family_match.group(1))

    return {
        "tree_id": tree_id,
        "lineage_name": lineage_name,
        "location": location,
        "generation_count": generation_count,
        "family_count": family_count,
        "people_count": people_count,
        "manager_name": manager_name,
        "manager_contact": None,
    }


def parse_pha_ky_text(html: str) -> str:
    section_match = re.search(
        r"<section[^>]*>\s*<h2>\s*Phả ký gia sử\s*</h2>\s*(.*?)</section>",
        html,
        flags=re.IGNORECASE | re.DOTALL,
    )
    if section_match and _clean_html_text(section_match.group(1)):
        body = section_match.group(1)
    else:
        after_heading = re.search(
            r"<h2>\s*Phả ký gia sử\s*</h2>\s*(.*?)(?:</main>|$)",
            html,
            flags=re.IGNORECASE | re.DOTALL,
        )
        if after_heading:
            body = after_heading.group(1)
        else:
            main_match = re.search(r"<main>(.*?)</main>", html, flags=re.IGNORECASE | re.DOTALL)
            body = main_match.group(1) if main_match else html

    body = re.sub(r"<script[^>]*>.*?</script>", " ", body, flags=re.IGNORECASE | re.DOTALL)
    body = re.sub(r"<style[^>]*>.*?</style>", " ", body, flags=re.IGNORECASE | re.DOTALL)
    body = re.sub(r"<nav[^>]*>.*?</nav>", " ", body, flags=re.IGNORECASE | re.DOTALL)
    body = re.sub(r"<br\s*/?>", "\n", body, flags=re.IGNORECASE)
    body = re.sub(r"</div>\s*", "\n", body, flags=re.IGNORECASE)
    body = re.sub(r"</p>\s*", "\n\n", body, flags=re.IGNORECASE)
    body = re.sub(r"<[^>]+>", " ", body)
    body = unescape(body).replace("\xa0", " ")

    lines = [re.sub(r"[ \t]+", " ", line).strip() for line in body.splitlines()]
    lines = [line for line in lines if line and line.lower() != "phả ký gia sử"]
    text = "\n\n".join(lines).strip()
    return text + ("\n" if text else "")


def _node_record_from_item(item: NodeItem, *, label: str) -> Dict[str, Any]:
    return {
        "tree_id": item.tree_id,
        "node_id": item.node_id,
        "label": label,
        "name": item.name,
        "generation": item.generation,
        "order_in_generation": item.order_in_generation,
        "gender": item.gender,
    }


def _parse_modern_gt_line(line: str, *, tree_id: int) -> List[Dict[str, Any]]:
    if not line.strip():
        return []

    gen_match = _GEN_ORDER_PATTERN.search(line)
    generation = int(gen_match.group(1)) if gen_match else None
    order = int(gen_match.group(2)) if gen_match else None

    links = list(_LINK_PATTERN.finditer(line))
    if not links:
        plain = _clean_html_text(line)
        gen_plain = re.match(r"^(\d+)\.(\d+)\s+(.+)$", plain)
        if not gen_plain:
            return []
        generation = int(gen_plain.group(1))
        order = int(gen_plain.group(2))
        name = gen_plain.group(3).strip()
        synthetic_id = tree_id * 100000 + generation * 1000 + order
        return [
            {
                "tree_id": tree_id,
                "node_id": synthetic_id,
                "label": plain,
                "name": name,
                "generation": generation,
                "order_in_generation": order,
                "gender": None,
            }
        ]

    line_label = _clean_html_text(re.sub(r"<[^>]+>", " ", line))
    records: List[Dict[str, Any]] = []
    for index, link in enumerate(links):
        node_id = int(link.group("node_id"))
        name = _clean_html_text(link.group("name"))
        gender = None
        lowered = name.lower()
        if any(token in lowered for token in ("ông ", "ông.", "cụ ", "anh ", "huỳnh ", "huỳnh ", "võ ", "trần ")):
            if "thị" not in lowered and "vợ" not in lowered:
                gender = "male"
        if any(token in lowered for token in ("bà ", "bà.", "vợ", "chị ", " thị ")):
            gender = "female"

        records.append(
            {
                "tree_id": tree_id,
                "node_id": node_id,
                "label": line_label if index == 0 else name,
                "name": name,
                "generation": generation if index == 0 else None,
                "order_in_generation": order if index == 0 else None,
                "gender": gender,
            }
        )
    return records


def parse_pha_he(html: str, *, tree_id: int) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]], str]:
    mode = detect_pha_he_mode(html)

    if mode == "legacy_js":
        items = parse_legacy_nodes(html)
        relationships = [asdict(item) for item in infer_parent_relationships(items)]
        nodes = [
            _node_record_from_item(item, label=item.label)
            for item in items
        ]
        return nodes, relationships, mode

    gt_match = re.search(r'<div\s+class=["\']gt["\'][^>]*>(.*?)</div>', html, flags=re.IGNORECASE | re.DOTALL)
    source = gt_match.group(1) if gt_match else html
    lines = re.split(r"<br\s*/?>\s*|\n", source)

    nodes: List[Dict[str, Any]] = []
    seen_ids: set[int] = set()
    for line in lines:
        for record in _parse_modern_gt_line(line, tree_id=tree_id):
            node_id = int(record["node_id"])
            if node_id in seen_ids:
                continue
            seen_ids.add(node_id)
            nodes.append(record)

    if not nodes and mode != "modern_gt":
        items = parse_legacy_nodes(html)
        if items:
            relationships = [asdict(item) for item in infer_parent_relationships(items)]
            nodes = [_node_record_from_item(item, label=item.label) for item in items]
            return nodes, relationships, "legacy_js"

    relationships = _infer_relationships_from_generations(nodes)
    return nodes, relationships, mode if nodes else "unknown"


def _infer_relationships_from_generations(nodes: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    relationships: List[Dict[str, Any]] = []
    latest_by_generation: Dict[int, Dict[str, Any]] = {}

    ordered = sorted(
        nodes,
        key=lambda item: (
            int(item.get("generation") or 0),
            int(item.get("order_in_generation") or 0),
            int(item.get("node_id") or 0),
        ),
    )

    for node in ordered:
        generation = node.get("generation")
        if not isinstance(generation, int):
            continue
        if generation > 1:
            parent = latest_by_generation.get(generation - 1)
            if parent is not None:
                side = "mid" if parent.get("gender") == "female" else "fid"
                relationships.append(
                    {
                        "type": "parent_of",
                        "from_id": int(parent["node_id"]),
                        "to_id": int(node["node_id"]),
                        "side": side,
                        "confidence": 0.65,
                        "rule": "generation_stack",
                    }
                )
        latest_by_generation[generation] = node

    return relationships


def parse_images(html: str, *, base_url: str) -> List[Dict[str, str]]:
    from urllib.parse import urljoin

    images: List[Dict[str, str]] = []
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


def hash_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def compute_vgp_content_hash(
    *,
    metadata: Dict[str, Any],
    nodes: List[Dict[str, Any]],
    pha_ky_text: Optional[str],
) -> str:
    payload = {
        "metadata": metadata,
        "nodes": sorted(nodes, key=lambda item: int(item.get("node_id") or 0)),
        "pha_ky_hash": hash_text(pha_ky_text) if pha_ky_text else None,
    }
    encoded = json.dumps(payload, ensure_ascii=False, sort_keys=True).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()
