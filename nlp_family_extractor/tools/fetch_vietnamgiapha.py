from __future__ import annotations

import argparse
import json
import re
import time
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from html import unescape
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import httpx


BASE_URL_TEMPLATE = "https://vietnamgiapha.com/XemPhaHe/{tree_id}/cay_pha_he.html"


@dataclass
class NodeItem:
    tree_id: int
    node_id: int
    label: str
    name: str
    generation: Optional[int]
    order_in_generation: Optional[int]
    gender: Optional[str]


@dataclass
class RelationshipItem:
    type: str
    from_id: int
    to_id: int
    side: str
    confidence: float
    rule: str


def _clean_html_text(value: str) -> str:
    value = re.sub(r"<[^>]+>", " ", value)
    value = unescape(value)
    value = value.replace("\xa0", " ")
    value = re.sub(r"\s+", " ", value)
    return value.strip()


def _split_label(label: str) -> Tuple[Optional[int], Optional[int], str]:
    cleaned = label.strip()
    match = re.match(r"^(\d+)\.(\d+)\s*(.*)$", cleaned)
    if not match:
        return None, None, cleaned
    generation = int(match.group(1))
    order = int(match.group(2))
    name = match.group(3).strip() or cleaned
    return generation, order, name


def _extract_title(html: str) -> Optional[str]:
    match = re.search(r"<title[^>]*>(.*?)</title>", html, flags=re.IGNORECASE | re.DOTALL)
    if not match:
        return None
    return _clean_html_text(match.group(1))


def parse_nodes(html: str) -> List[NodeItem]:
    # Match the common pattern: optional gender icon image, then a javascript:o(tree_id,node_id) link.
    pattern = re.compile(
        r"(?:treeimg/(?P<gender>[mf])\.jpg[^>]*>\s*)?"
        r"<a[^>]+href=[\"']javascript:o\((?P<tree_id>\d+),(?P<node_id>\d+)\)[\"'][^>]*>"
        r"(?P<label>.*?)</a>",
        flags=re.IGNORECASE | re.DOTALL,
    )

    nodes: List[NodeItem] = []
    seen: set[Tuple[int, int]] = set()

    for match in pattern.finditer(html):
        tree_id = int(match.group("tree_id"))
        node_id = int(match.group("node_id"))
        key = (tree_id, node_id)
        if key in seen:
            continue
        seen.add(key)

        raw_label = _clean_html_text(match.group("label"))
        generation, order, name = _split_label(raw_label)
        raw_gender = (match.group("gender") or "").lower()
        gender: Optional[str] = None
        if raw_gender == "m":
            gender = "male"
        elif raw_gender == "f":
            gender = "female"

        nodes.append(
            NodeItem(
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


def infer_parent_relationships(nodes: List[NodeItem]) -> List[RelationshipItem]:
    """Infer parent_of edges from generation numbers using traversal-order stack.

    Rule:
    - Track the latest seen node for each generation while scanning HTML order.
    - A node in generation g gets parent from latest seen generation g-1.
    - Parent side inferred by gender: male->fid, female->mid, unknown->fid.
    """
    relationships: List[RelationshipItem] = []
    latest_by_generation: Dict[int, NodeItem] = {}

    for node in nodes:
        if node.generation is None or node.generation <= 1:
            if node.generation is not None:
                latest_by_generation[node.generation] = node
            continue

        parent = latest_by_generation.get(node.generation - 1)
        if parent is not None:
            side = "fid"
            if parent.gender == "female":
                side = "mid"
            relationships.append(
                RelationshipItem(
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


def fetch_page(client: httpx.Client, tree_id: int) -> httpx.Response:
    url = BASE_URL_TEMPLATE.format(tree_id=tree_id)
    return client.get(url)


def run(
    start_id: int,
    end_id: int,
    output_dir: Path,
    save_html: bool,
    delay_seconds: float,
    timeout_seconds: float,
) -> Dict[str, Any]:
    output_dir.mkdir(parents=True, exist_ok=True)
    json_dir = output_dir / "json"
    json_dir.mkdir(parents=True, exist_ok=True)
    html_dir = output_dir / "raw_html"
    if save_html:
        html_dir.mkdir(parents=True, exist_ok=True)

    summary: Dict[str, Any] = {
        "start_id": start_id,
        "end_id": end_id,
        "fetched_at": datetime.now(timezone.utc).isoformat(),
        "success": [],
        "errors": [],
    }

    headers = {
        "User-Agent": "family-tree-research-tool/1.0 (+https://github.com)"
    }

    with httpx.Client(follow_redirects=True, timeout=timeout_seconds, headers=headers) as client:
        for tree_id in range(start_id, end_id + 1):
            url = BASE_URL_TEMPLATE.format(tree_id=tree_id)
            try:
                response = fetch_page(client, tree_id)
                response.raise_for_status()
                html = response.text
                nodes = parse_nodes(html)
                relationships = infer_parent_relationships(nodes)

                parent_by_child: Dict[int, Dict[str, Any]] = {}
                for rel in relationships:
                    # Keep one inferred parent per side for child node.
                    child_entry = parent_by_child.setdefault(rel.to_id, {})
                    if rel.side not in child_entry:
                        child_entry[rel.side] = rel.from_id

                nodes_with_relationships: List[Dict[str, Any]] = []
                for item in nodes:
                    record = asdict(item)
                    if item.node_id in parent_by_child:
                        record.update(parent_by_child[item.node_id])
                    nodes_with_relationships.append(record)

                page_data: Dict[str, Any] = {
                    "tree_id": tree_id,
                    "url": url,
                    "http_status": response.status_code,
                    "title": _extract_title(html),
                    "node_count": len(nodes),
                    "relationship_count": len(relationships),
                    "relationships": [asdict(item) for item in relationships],
                    "nodes": nodes_with_relationships,
                }

                out_file = json_dir / f"{tree_id}.json"
                out_file.write_text(
                    json.dumps(page_data, ensure_ascii=False, indent=2) + "\n",
                    encoding="utf-8",
                )

                if save_html:
                    html_file = html_dir / f"{tree_id}.html"
                    html_file.write_text(html, encoding="utf-8")

                summary["success"].append(
                    {
                        "tree_id": tree_id,
                        "url": url,
                        "node_count": len(nodes),
                        "output": str(out_file),
                    }
                )
            except Exception as exc:  # pragma: no cover - network safety
                summary["errors"].append(
                    {
                        "tree_id": tree_id,
                        "url": url,
                        "error": str(exc),
                    }
                )

            if delay_seconds > 0:
                time.sleep(delay_seconds)

    summary_file = output_dir / "summary.json"
    summary_file.write_text(
        json.dumps(summary, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return summary


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Fetch vietnamgiapha tree pages in an ID range and save structured JSON results."
        )
    )
    parser.add_argument("--start", type=int, default=100, help="Start tree_id (inclusive).")
    parser.add_argument("--end", type=int, default=200, help="End tree_id (inclusive).")
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("data/vietnamgiapha"),
        help="Directory to write output files.",
    )
    parser.add_argument(
        "--save-html",
        action="store_true",
        help="Also persist raw HTML for each page.",
    )
    parser.add_argument(
        "--delay-seconds",
        type=float,
        default=0.5,
        help="Delay between requests to reduce load on target server.",
    )
    parser.add_argument(
        "--timeout-seconds",
        type=float,
        default=20.0,
        help="HTTP timeout for each request.",
    )
    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    if args.start > args.end:
        raise SystemExit("--start must be <= --end")

    summary = run(
        start_id=args.start,
        end_id=args.end,
        output_dir=args.output_dir,
        save_html=args.save_html,
        delay_seconds=args.delay_seconds,
        timeout_seconds=args.timeout_seconds,
    )

    success_count = len(summary.get("success", []))
    error_count = len(summary.get("errors", []))
    print(f"Done. success={success_count}, errors={error_count}")
    print(f"Summary: {args.output_dir / 'summary.json'}")


if __name__ == "__main__":
    main()
