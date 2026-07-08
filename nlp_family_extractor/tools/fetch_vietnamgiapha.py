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

from tools.vietnamgiapha_text_export import (
    compute_content_hash,
    export_tree_text_files,
)


BASE_URL_TEMPLATE = "https://vietnamgiapha.com/XemPhaHe/{tree_id}/cay_pha_he.html"
DETAIL_URL_TEMPLATES = [
    "https://vietnamgiapha.com/XemChiTietTungNguoi/{tree_id}/{node_id}/giapha.html",
    "https://vietnamgiapha.com/XemChiTietTungNguoi/{tree_id}/{node_id}/chitiet.html",
]


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


def _extract_lineage_name(html: str) -> Optional[str]:
    # Sidebar block usually contains: GIA / PHẢ / TỘC / <lineage name>
    # We extract text from that TD and remove the fixed heading words.
    match = re.search(
        r"<TD[^>]*background=[\"'](?:https?://(?:www\.)?vietnamgiapha\.com)?/giapha_tml/oldbook(?:/|//)images/mid\.gif[\"'][^>]*>(?P<body>.*?)</TD>",
        html,
        flags=re.IGNORECASE | re.DOTALL,
    )
    if not match:
        # Fallback: locate by the heading sequence itself.
        match = re.search(
            r"<TD[^>]*>(?P<body>.*?<p>\s*GIA\s*</p>\s*<p>\s*PH[^<]*</p>\s*<p>\s*T[^<]*</p>.*?)(?:</TD>)",
            html,
            flags=re.IGNORECASE | re.DOTALL,
        )
    if not match:
        return None

    body = match.group("body")

    # Prefer extracting the trailing content after the 3 heading <p> tags.
    after_heading = re.sub(
        r"^\s*(?:<p>\s*GIA\s*</p>\s*<p>\s*PHẢ\s*</p>\s*<p>\s*TỘC\s*</p>\s*)",
        "",
        body,
        flags=re.IGNORECASE | re.DOTALL,
    )
    text = _clean_html_text(after_heading)

    if not text:
        text = _clean_html_text(body)
        text = re.sub(r"\bGIA\b", " ", text, flags=re.IGNORECASE)
        text = re.sub(r"\bPHẢ\b", " ", text, flags=re.IGNORECASE)
        text = re.sub(r"\bTỘC\b", " ", text, flags=re.IGNORECASE)
        text = re.sub(r"\s+", " ", text).strip()

    if not text:
        return None
    return text


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


def _extract_int_year(value: str) -> Optional[int]:
    match = re.search(r"(1[6-9]\d{2}|20\d{2})", value)
    if not match:
        return None
    return int(match.group(1))


def _extract_node_ids_from_links(html: str, tree_id: int) -> List[int]:
    pattern = re.compile(
        rf"/XemChiTietTungNguoi/{tree_id}/(?P<node_id>\d+)/",
        flags=re.IGNORECASE,
    )
    found: List[int] = []
    for m in pattern.finditer(html):
        nid = int(m.group("node_id"))
        if nid not in found:
            found.append(nid)
    return found


def _extract_detail_fields(html: str, tree_id: int, node_id: int, detail_url: str) -> Dict[str, Any]:
    fields: Dict[str, Any] = {
        "detail_url": detail_url,
    }

    title = _extract_title(html)
    if title:
        fields["detail_title"] = title

    # Parse key-value rows in profile table.
    row_pattern = re.compile(
        r"<td[^>]*style=[\"'][^\"']*font-weight\s*:\s*bold[^\"']*[\"'][^>]*>(?P<label>.*?)</td>\s*"
        r"<td[^>]*>(?P<value>.*?)</td>",
        flags=re.IGNORECASE | re.DOTALL,
    )
    kv: Dict[str, str] = {}
    for m in row_pattern.finditer(html):
        label = _clean_html_text(m.group("label")).rstrip(":")
        value = _clean_html_text(m.group("value"))
        if label:
            kv[label] = value

    detail_name = kv.get("Tên")
    if detail_name:
        fields["display_name"] = detail_name
        if "(Nam)" in detail_name:
            fields["gender_hint"] = "male"
        elif "(Nữ)" in detail_name or "(Nu)" in detail_name:
            fields["gender_hint"] = "female"

    if kv.get("Tên thường"):
        fields["common_name"] = kv["Tên thường"]
    if kv.get("Tên Tự"):
        fields["courtesy_name"] = kv["Tên Tự"]
    if kv.get("Thụy hiệu"):
        fields["epithet"] = kv["Thụy hiệu"]
    if kv.get("Ngày sinh"):
        fields["birth_text"] = kv["Ngày sinh"]
        year = _extract_int_year(kv["Ngày sinh"])
        if year is not None:
            fields["birth_year"] = year
    if kv.get("Ngày mất"):
        fields["death_text"] = kv["Ngày mất"]
        year = _extract_int_year(kv["Ngày mất"])
        if year is not None:
            fields["death_year"] = year
    if kv.get("Nơi an táng"):
        fields["burial_place"] = kv["Nơi an táng"]

    # Generation and parent hint often appear outside table rows.
    gen_match = re.search(r"Đời thứ\s*:\s*(\d+)", html, flags=re.IGNORECASE)
    if gen_match:
        fields["generation_text"] = int(gen_match.group(1))

    parent_match = re.search(
        r"Là con của\s*:\s*(.*?)</td>",
        html,
        flags=re.IGNORECASE | re.DOTALL,
    )
    if parent_match:
        fields["parent_text"] = _clean_html_text(parent_match.group(1))

    note_match = re.search(
        r"Sự nghiệp,\s*công đức,\s*ghi chú\s*</td>\s*</tr>\s*<tr>\s*<td[^>]*>(.*?)</td>",
        html,
        flags=re.IGNORECASE | re.DOTALL,
    )
    if note_match:
        fields["note"] = _clean_html_text(note_match.group(1))

    sibling_match = re.search(
        r"<b>\s*Các anh em, dâu rể:\s*</b>(.*?)</td>",
        html,
        flags=re.IGNORECASE | re.DOTALL,
    )
    if sibling_match:
        fields["siblings_text"] = _clean_html_text(sibling_match.group(1))

    child_match = re.search(
        r"<b>\s*Con cái:\s*</b>(.*?)</td>",
        html,
        flags=re.IGNORECASE | re.DOTALL,
    )
    if child_match:
        child_html = child_match.group(1)
        child_names = re.findall(r">([^<]+)</a>", child_html, flags=re.IGNORECASE)
        fields["children_names"] = [_clean_html_text(x) for x in child_names if _clean_html_text(x)]
        fields["children_node_ids"] = _extract_node_ids_from_links(child_html, tree_id)

    fields["tree_id"] = tree_id
    fields["node_id"] = node_id
    return fields


def fetch_detail_profile(
    client: httpx.Client,
    *,
    tree_id: int,
    node_id: int,
) -> Optional[Dict[str, Any]]:
    for template in DETAIL_URL_TEMPLATES:
        detail_url = template.format(tree_id=tree_id, node_id=node_id)
        try:
            response = client.get(detail_url)
            if response.status_code != 200:
                continue
            html = response.text
            if "Chi tiết gia đình" not in html and "Người trong gia đình" not in html:
                continue
            return _extract_detail_fields(html, tree_id=tree_id, node_id=node_id, detail_url=detail_url)
        except Exception:
            continue
    return None


def _load_existing_page_data(out_file: Path) -> Optional[Dict[str, Any]]:
    if not out_file.exists():
        return None
    try:
        data = json.loads(out_file.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    return data if isinstance(data, dict) else None


def run(
    start_id: int,
    end_id: int,
    output_dir: Path,
    save_html: bool,
    fetch_detail: bool,
    detail_delay_seconds: float,
    delay_seconds: float,
    timeout_seconds: float,
    skip_empty: bool = True,
    skip_unchanged: bool = False,
    export_text: bool = True,
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
        "skipped": [],
        "skipped_unchanged": [],
        "text_built": [],
        "text_skipped": [],
        "errors": [],
    }

    headers = {
        "User-Agent": "family-tree-research-tool/1.0 (+https://github.com)"
    }

    with httpx.Client(follow_redirects=True, timeout=timeout_seconds, headers=headers) as client:
        for tree_id in range(start_id, end_id + 1):
            url = BASE_URL_TEMPLATE.format(tree_id=tree_id)
            out_file = json_dir / f"{tree_id}.json"
            html_file = html_dir / f"{tree_id}.html"

            try:
                if skip_unchanged:
                    existing = _load_existing_page_data(out_file)
                    if existing and existing.get("node_count", 0) > 0:
                        existing_hash = existing.get("content_hash") or compute_content_hash(existing)
                        if export_text:
                            built, _ = export_tree_text_files(
                                existing,
                                output_root=output_dir,
                                force=False,
                            )
                            if built:
                                summary["text_built"].append({"tree_id": tree_id, "mode": "from_existing_json"})
                            else:
                                summary["text_skipped"].append({"tree_id": tree_id, "reason": "text_exists"})
                        summary["skipped_unchanged"].append(
                            {
                                "tree_id": tree_id,
                                "url": url,
                                "content_hash": existing_hash,
                                "reason": "unchanged",
                            }
                        )
                        if delay_seconds > 0:
                            time.sleep(delay_seconds)
                        continue

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
                detail_fetched_count = 0
                for item in nodes:
                    record = asdict(item)
                    if item.node_id in parent_by_child:
                        record.update(parent_by_child[item.node_id])

                    if fetch_detail:
                        detail = fetch_detail_profile(
                            client,
                            tree_id=tree_id,
                            node_id=item.node_id,
                        )
                        if detail:
                            record["detail"] = detail
                            detail_fetched_count += 1
                            if detail.get("gender_hint") in ("male", "female") and not record.get("gender"):
                                record["gender"] = detail["gender_hint"]
                            if isinstance(detail.get("birth_year"), int):
                                record["birthYear"] = detail["birth_year"]
                            if isinstance(detail.get("death_year"), int):
                                record["deathYear"] = detail["death_year"]
                            if isinstance(detail.get("note"), str) and detail["note"]:
                                record["bio"] = detail["note"]

                        if detail_delay_seconds > 0:
                            time.sleep(detail_delay_seconds)

                    nodes_with_relationships.append(record)

                page_data: Dict[str, Any] = {
                    "tree_id": tree_id,
                    "url": url,
                    "http_status": response.status_code,
                    "title": _extract_title(html),
                    "lineage_name": _extract_lineage_name(html),
                    "node_count": len(nodes),
                    "detail_fetched_count": detail_fetched_count,
                    "relationship_count": len(relationships),
                    "relationships": [asdict(item) for item in relationships],
                    "nodes": nodes_with_relationships,
                }
                page_data["content_hash"] = compute_content_hash(page_data)

                if skip_empty and len(nodes) == 0:
                    if out_file.exists():
                        out_file.unlink()
                    if html_file.exists():
                        html_file.unlink()
                    summary["skipped"].append(
                        {
                            "tree_id": tree_id,
                            "url": url,
                            "reason": "empty_tree",
                        }
                    )
                    if delay_seconds > 0:
                        time.sleep(delay_seconds)
                    continue

                out_file.write_text(
                    json.dumps(page_data, ensure_ascii=False, indent=2) + "\n",
                    encoding="utf-8",
                )

                if save_html:
                    html_file.write_text(html, encoding="utf-8")

                if export_text:
                    built, _ = export_tree_text_files(page_data, output_root=output_dir, force=True)
                    if built:
                        summary["text_built"].append({"tree_id": tree_id, "mode": "fresh_crawl"})
                    else:
                        summary["text_skipped"].append({"tree_id": tree_id, "reason": "text_exists"})

                summary["success"].append(
                    {
                        "tree_id": tree_id,
                        "url": url,
                        "node_count": len(nodes),
                        "content_hash": page_data["content_hash"],
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
        "--keep-empty",
        action="store_true",
        help="Keep output files even when node_count=0 (default is skip).",
    )
    parser.add_argument(
        "--no-detail",
        action="store_true",
        help="Skip fetching per-person detail pages.",
    )
    parser.add_argument(
        "--detail-delay-seconds",
        type=float,
        default=0.05,
        help="Delay between detail-page requests.",
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
    parser.add_argument(
        "--skip-unchanged",
        action="store_true",
        help="Skip HTTP fetch when local JSON exists and content_hash is unchanged.",
    )
    parser.add_argument(
        "--no-export-text",
        action="store_true",
        help="Do not build text/{tree_id}/ exports.",
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
        fetch_detail=not args.no_detail,
        detail_delay_seconds=args.detail_delay_seconds,
        delay_seconds=args.delay_seconds,
        timeout_seconds=args.timeout_seconds,
        skip_empty=not args.keep_empty,
        skip_unchanged=args.skip_unchanged,
        export_text=not args.no_export_text,
    )

    success_count = len(summary.get("success", []))
    skipped_count = len(summary.get("skipped", []))
    skipped_unchanged_count = len(summary.get("skipped_unchanged", []))
    error_count = len(summary.get("errors", []))
    print(
        "Done. "
        f"success={success_count}, skipped={skipped_count}, "
        f"skipped_unchanged={skipped_unchanged_count}, errors={error_count}"
    )
    print(f"Summary: {args.output_dir / 'summary.json'}")


if __name__ == "__main__":
    main()
