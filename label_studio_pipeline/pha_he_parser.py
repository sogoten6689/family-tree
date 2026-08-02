"""Parse vietnamgiapha.com phả hệ (sơ đồ) pages."""

from __future__ import annotations

import re
from dataclasses import asdict, dataclass
from html import unescape
from typing import Any

from bs4 import BeautifulSoup, NavigableString, Tag

from label_studio_pipeline.html_utils import extract_lineage_name, extract_title, normalize_whitespace

NODE_ID_PATTERN = re.compile(r"/XemChiTietTungNguoi/\d+/(\d+)/", re.IGNORECASE)
GEN_ORDER_PATTERN = re.compile(r"^(\d+)\.(\d+)$")
LEGACY_NODE_PATTERN = re.compile(
    r"(?:treeimg/(?P<gender>[mf])\.jpg[^>]*>\s*)?"
    r"<a[^>]+href=[\"']javascript:o\((?P<tree_id>\d+),(?P<node_id>\d+)\)[\"'][^>]*>"
    r"(?P<label>.*?)</a>",
    flags=re.IGNORECASE | re.DOTALL,
)
SPOUSE_HINT_PATTERN = re.compile(r"\((?:vợ|vo|chồng|chong|chồng\s*)\)", re.IGNORECASE)


@dataclass
class ParsedNode:
    tree_id: int
    node_id: int
    label: str
    name: str
    generation: int | None
    order_in_generation: int | None
    gender: str | None
    is_spouse_row: bool = False


@dataclass
class ParsedRelationship:
    type: str
    from_id: int
    to_id: int
    side: str
    confidence: float
    rule: str


def _clean_label(value: str) -> str:
    value = re.sub(r"<[^>]+>", " ", value)
    value = unescape(value)
    return normalize_whitespace(value)


def _split_gen_order(raw: str) -> tuple[int | None, int | None]:
    match = GEN_ORDER_PATTERN.match(raw.strip())
    if not match:
        return None, None
    return int(match.group(1)), int(match.group(2))


def _split_person_label(label: str) -> tuple[int | None, int | None, str]:
    cleaned = label.strip()
    match = re.match(r"^(\d+)\.(\d+)\s*(.*)$", cleaned)
    if not match:
        return None, None, cleaned
    return int(match.group(1)), int(match.group(2)), match.group(3).strip() or cleaned


def _extract_node_id(href: str | None) -> int | None:
    if not href:
        return None
    match = NODE_ID_PATTERN.search(href)
    if not match:
        return None
    return int(match.group(1))


def _is_spouse_link(text: str) -> bool:
    lowered = text.lower()
    if SPOUSE_HINT_PATTERN.search(text):
        return True
    if "cập nhật sau" in lowered:
        return True
    return False


def _iter_tree_view_lines(tree_view: Tag) -> list[list[Any]]:
    lines: list[list[Any]] = []
    current: list[Any] = []
    for child in tree_view.children:
        if isinstance(child, NavigableString):
            if str(child).strip():
                current.append(child)
            continue
        if getattr(child, "name", None) == "br":
            if current:
                lines.append(current)
                current = []
            continue
        current.append(child)
    if current:
        lines.append(current)
    return lines


def _parse_tree_view_line(tree_id: int, line_nodes: list[Any]) -> ParsedNode | None:
    generation: int | None = None
    order: int | None = None
    links: list[tuple[int, str]] = []

    for item in line_nodes:
        if isinstance(item, Tag):
            if item.name == "b":
                generation, order = _split_gen_order(item.get_text(strip=True))
            elif item.name == "a":
                node_id = _extract_node_id(item.get("href"))
                text = normalize_whitespace(item.get_text())
                if node_id is not None and text:
                    links.append((node_id, text))

    if not links:
        return None

    primary_id, primary_name = links[0]
    label_parts = []
    if generation is not None and order is not None:
        label_parts.append(f"{generation}.{order}")
    label_parts.append(primary_name)
    label = " ".join(label_parts)

    return ParsedNode(
        tree_id=tree_id,
        node_id=primary_id,
        label=label,
        name=primary_name,
        generation=generation,
        order_in_generation=order,
        gender=None,
        is_spouse_row=_is_spouse_link(primary_name),
    )


def _parse_tree_view(tree_view: Tag, tree_id: int) -> list[ParsedNode]:
    nodes: list[ParsedNode] = []
    seen: set[int] = set()
    for line in _iter_tree_view_lines(tree_view):
        parsed = _parse_tree_view_line(tree_id, line)
        if parsed is None or parsed.node_id in seen:
            continue
        seen.add(parsed.node_id)
        nodes.append(parsed)
    return nodes


def _parse_legacy_js(html: str, tree_id: int) -> list[ParsedNode]:
    nodes: list[ParsedNode] = []
    seen: set[int] = set()
    for match in LEGACY_NODE_PATTERN.finditer(html):
        node_id = int(match.group("node_id"))
        if node_id in seen:
            continue
        seen.add(node_id)
        raw_label = _clean_label(match.group("label"))
        generation, order, name = _split_person_label(raw_label)
        raw_gender = (match.group("gender") or "").lower()
        gender = "male" if raw_gender == "m" else "female" if raw_gender == "f" else None
        nodes.append(
            ParsedNode(
                tree_id=tree_id,
                node_id=node_id,
                label=raw_label,
                name=name,
                generation=generation,
                order_in_generation=order,
                gender=gender,
            )
        )
    return nodes


def infer_parent_relationships(nodes: list[ParsedNode]) -> list[ParsedRelationship]:
    relationships: list[ParsedRelationship] = []
    latest_by_generation: dict[int, ParsedNode] = {}

    for node in nodes:
        if node.is_spouse_row:
            continue
        if node.generation is None or node.generation <= 1:
            if node.generation is not None:
                latest_by_generation[node.generation] = node
            continue

        parent = latest_by_generation.get(node.generation - 1)
        if parent is not None:
            side = "mid" if parent.gender == "female" else "fid"
            relationships.append(
                ParsedRelationship(
                    type="parent_of",
                    from_id=parent.node_id,
                    to_id=node.node_id,
                    side=side,
                    confidence=0.65,
                    rule="generation_stack",
                )
            )
        latest_by_generation[node.generation] = node

    return relationships


def nodes_to_plain_text(nodes: list[ParsedNode]) -> str:
    lines: list[str] = []
    for node in nodes:
        prefix = ""
        if node.generation is not None and node.order_in_generation is not None:
            prefix = f"{node.generation}.{node.order_in_generation} "
        lines.append(f"{prefix}{node.name}")
    return "\n".join(lines)


def parse_pha_he_html(
    html: str,
    *,
    tree_id: int,
    source_url: str,
) -> dict[str, Any]:
    """Parse pha_he.html (or legacy cay_pha_he) into structured JSON."""
    soup = BeautifulSoup(html, "html.parser")
    lineage_name = extract_lineage_name(soup) or extract_title(soup)

    tree_view = soup.select_one(".tree-view")
    if tree_view is not None:
        nodes = _parse_tree_view(tree_view, tree_id)
        parser_mode = "tree_view"
    else:
        nodes = _parse_legacy_js(html, tree_id)
        parser_mode = "legacy_javascript_o"

    relationships = infer_parent_relationships(nodes)
    return {
        "tree_id": tree_id,
        "source_url": source_url,
        "lineage_name": lineage_name,
        "parser_mode": parser_mode,
        "node_count": len(nodes),
        "relationship_count": len(relationships),
        "nodes": [asdict(n) for n in nodes],
        "relationships": [asdict(r) for r in relationships],
    }
