#!/usr/bin/env python3
"""BalkanNode[] JSON → sơ đồ gia phả HTML tĩnh, 1 file/gia đình. Không Docker, không server.

Free-only (docs/planning/output_formats_and_ui_plan.md Phụ lục C — .cursor/rules/free-only-visualization.mdc):
thuần HTML/CSS tự viết, không gọi thư viện/nền tảng bên thứ ba, không gửi nodes_json ra ngoài máy.
"Gia đình" = một thành phần liên thông (nối bằng fid/mid/pids) trong file nodes.json — mỗi thành
phần ra một file HTML riêng, mở trực tiếp bằng trình duyệt (file://), không cần backend/MySQL.

  python nlp_family_extractor/tools/render_family_tree.py \
      --nodes data/01_interim/huong_nguyen_ke/nguyen-ke.nodes.json \
      --out-dir data/01_interim/huong_nguyen_ke/tree
"""

from __future__ import annotations

import argparse
import html
import json
import re
import unicodedata
from pathlib import Path
from typing import Any

_TOOLS = Path(__file__).resolve().parent
REPO = _TOOLS.parents[1]


def load_nodes(path: Path) -> list[dict[str, Any]]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if isinstance(data, list):
        return data
    if isinstance(data, dict) and isinstance(data.get("nodes"), list):
        return data["nodes"]
    raise SystemExit(f"{path}: không nhận ra định dạng (cần BalkanNode[] hoặc {{nodes: [...]}})")


def slugify(text: str) -> str:
    text = text.replace("đ", "d").replace("Đ", "D")
    norm = unicodedata.normalize("NFKD", text)
    ascii_text = norm.encode("ascii", "ignore").decode("ascii")
    slug = re.sub(r"[^a-zA-Z0-9]+", "-", ascii_text).strip("-").lower()
    return slug or "gia-dinh"


class UnionFind:
    def __init__(self, ids: list[int]) -> None:
        self.parent = {i: i for i in ids}

    def find(self, x: int) -> int:
        while self.parent[x] != x:
            self.parent[x] = self.parent[self.parent[x]]
            x = self.parent[x]
        return x

    def union(self, a: int, b: int) -> None:
        ra, rb = self.find(a), self.find(b)
        if ra != rb:
            self.parent[ra] = rb


def group_families(nodes: list[dict[str, Any]]) -> list[list[dict[str, Any]]]:
    by_id = {int(n["id"]): n for n in nodes}
    uf = UnionFind(list(by_id.keys()))
    for n in nodes:
        nid = int(n["id"])
        for key in ("fid", "mid"):
            other = n.get(key)
            if other is not None and int(other) in by_id:
                uf.union(nid, int(other))
        for other in n.get("pids") or []:
            if int(other) in by_id:
                uf.union(nid, int(other))

    groups: dict[int, list[dict[str, Any]]] = {}
    for nid in by_id:
        groups.setdefault(uf.find(nid), []).append(by_id[nid])
    ordered = sorted(groups.values(), key=lambda g: min(int(p["id"]) for p in g))
    return ordered


def person_label(p: dict[str, Any]) -> str:
    years = ""
    b, d = p.get("birthYear"), p.get("deathYear")
    if b or d:
        years = f" ({b or '?'}–{d or '?'})"
    return f"{p.get('name', '?')}{years}"


CARD_TEMPLATE = """<div class="card {gender}">
  <div class="name">{name}</div>
  {title_html}
  {years_html}
  {bio_html}
</div>"""


def render_card(p: dict[str, Any]) -> str:
    gender = "male" if p.get("gender") == "male" else "female" if p.get("gender") == "female" else "unknown"
    name = html.escape(str(p.get("name") or "?"))
    title_html = f'<div class="title">{html.escape(str(p["title"]))}</div>' if p.get("title") else ""
    b, d = p.get("birthYear"), p.get("deathYear")
    years_html = f'<div class="years">{b or "?"}–{d or "?"}</div>' if (b or d) else ""
    bio = p.get("bio")
    bio_html = f'<div class="bio">{html.escape(str(bio))}</div>' if bio else ""
    return CARD_TEMPLATE.format(
        gender=gender, name=name, title_html=title_html, years_html=years_html, bio_html=bio_html
    )


def render_family(family: list[dict[str, Any]]) -> tuple[str, str]:
    by_id = {int(p["id"]): p for p in family}
    ids = set(by_id)

    children_of: dict[int, list[int]] = {}
    for p in family:
        pid = int(p["id"])
        for key in ("fid", "mid"):
            parent = p.get(key)
            if parent is not None and int(parent) in ids:
                children_of.setdefault(int(parent), []).append(pid)

    def has_parent_in_family(p: dict[str, Any]) -> bool:
        for key in ("fid", "mid"):
            v = p.get(key)
            if v is not None and int(v) in ids:
                return True
        return False

    roots = [p for p in family if not has_parent_in_family(p)]

    # Suy luận cặp vợ chồng còn thiếu `pids` đối xứng: 2 root cùng có ít nhất 1 con
    # chung (qua fid/mid) nhưng không khai pids — gap thường gặp khi nodes.json đến
    # từ POST /api/family-tree/analyze (Gemini không luôn gán pids cho cặp gốc).
    root_ids = [int(r["id"]) for r in roots]
    for i, a in enumerate(root_ids):
        for b in root_ids[i + 1 :]:
            a_children = set(children_of.get(a, []))
            b_children = set(children_of.get(b, []))
            if a_children & b_children:
                pa, pb = by_id[a], by_id[b]
                pa_pids = list(pa.get("pids") or [])
                pb_pids = list(pb.get("pids") or [])
                if b not in pa_pids:
                    pa_pids.append(b)
                if a not in pb_pids:
                    pb_pids.append(a)
                pa["pids"], pb["pids"] = pa_pids, pb_pids

    roots.sort(key=lambda p: (p.get("birthYear") or 9999, p.get("name") or ""))

    rendered: set[int] = set()

    def render_person_node(pid: int) -> str:
        person = by_id[pid]
        spouses = [
            by_id[s] for s in (person.get("pids") or []) if int(s) in ids and int(s) not in rendered and int(s) != pid
        ]
        rendered.add(pid)
        cards = [render_card(person)]
        for sp in spouses:
            rendered.add(int(sp["id"]))
            cards.append('<div class="spouse-link">⚭</div>')
            cards.append(render_card(sp))

        child_ids: list[int] = list(children_of.get(pid, []))
        for sp in spouses:
            for c in children_of.get(int(sp["id"]), []):
                if c not in child_ids:
                    child_ids.append(c)
        child_ids = [c for c in child_ids if c not in rendered]
        child_ids.sort(key=lambda c: (by_id[c].get("birthYear") or 9999, by_id[c].get("name") or ""))

        children_html = ""
        if child_ids:
            items = "\n".join(f"<li>{render_person_node(c)}</li>" for c in child_ids)
            children_html = f'<ul class="children">\n{items}\n</ul>'

        return f'<div class="couple">{"".join(cards)}</div>\n{children_html}'

    forest_html = "\n".join(f'<li>{render_person_node(int(r["id"]))}</li>' for r in roots if int(r["id"]) not in rendered)

    title_person = roots[0] if roots else family[0]
    family_title = f"Gia đình {person_label(title_person)}"
    body = f'<ul class="tree">{forest_html}</ul>' if forest_html else "<p>(trống)</p>"
    return family_title, body


PAGE_TEMPLATE = """<!doctype html>
<html lang="vi">
<head>
<meta charset="utf-8">
<title>{title}</title>
<style>
{css}
</style>
</head>
<body>
<h1>{title}</h1>
<p class="meta">Nguồn: {source} — sinh tự động, không sửa tay. {count} người.</p>
{body}
</body>
</html>
"""

CSS = """
:root {
  --line: #b8a98a;
  --male-bg: #eaf2f8; --male-bd: #6f9fc4;
  --female-bg: #fbeef2; --female-bd: #c4708f;
  --unknown-bg: #f2f2ef; --unknown-bd: #999;
  --ink: #2b2620;
}
body { font-family: "Segoe UI", "Noto Sans", sans-serif; background: #faf7f0; color: var(--ink); margin: 2rem; }
h1 { font-size: 1.4rem; margin-bottom: 0.2rem; }
.meta { color: #7a7266; font-size: 0.85rem; margin-top: 0; margin-bottom: 2rem; }

.tree, .tree ul { list-style: none; margin: 0; padding: 0; position: relative; }
.tree { padding-top: 0; display: flex; }
.tree ul { padding-top: 2rem; display: flex; }
.tree li { float: left; text-align: center; position: relative; padding: 2rem 0.6rem 0 0.6rem; }
.tree > li { padding-top: 0; }

.tree li::before, .tree li::after {
  content: ""; position: absolute; top: 0; right: 50%; border-top: 2px solid var(--line); width: 50%; height: 2rem;
}
.tree li::after { right: auto; left: 50%; border-left: 2px solid var(--line); }
.tree li:only-child::before, .tree li:only-child::after { display: none; }
.tree li:only-child { padding-top: 0; }
.tree li:first-child::before { border: 0 none; }
.tree li:last-child::after { border: 0 none; }
.tree li:last-child::before { border-right: 2px solid var(--line); border-radius: 0 6px 0 0; }
.tree li:first-child::after { border-radius: 6px 0 0 0; }
.tree ul::before {
  content: ""; position: absolute; top: 0; left: 50%; border-left: 2px solid var(--line); width: 0; height: 2rem;
}

.couple { display: inline-flex; align-items: center; gap: 0.4rem; }
.spouse-link { color: #9c8a5f; font-size: 1rem; }

.card {
  display: inline-block; min-width: 8.5rem; max-width: 13rem; padding: 0.5rem 0.7rem; border-radius: 8px;
  border: 2px solid var(--unknown-bd); background: var(--unknown-bg); box-shadow: 1px 2px 3px rgba(0,0,0,0.08);
  text-align: left;
}
.card.male { background: var(--male-bg); border-color: var(--male-bd); }
.card.female { background: var(--female-bg); border-color: var(--female-bd); }
.card .name { font-weight: 600; font-size: 0.92rem; }
.card .title { font-size: 0.75rem; color: #8a6b2f; font-style: italic; }
.card .years { font-size: 0.78rem; color: #555; }
.card .bio { font-size: 0.72rem; color: #666; margin-top: 0.2rem; }

@media print {
  body { background: white; margin: 0.5cm; }
}
"""

INDEX_TEMPLATE = """<!doctype html>
<html lang="vi">
<head>
<meta charset="utf-8">
<title>{title}</title>
<style>
body {{ font-family: "Segoe UI", "Noto Sans", sans-serif; background: #faf7f0; color: #2b2620; margin: 2rem; }}
li {{ margin: 0.3rem 0; }}
a {{ color: #6f9fc4; text-decoration: none; }}
a:hover {{ text-decoration: underline; }}
</style>
</head>
<body>
<h1>{title}</h1>
<p>Nguồn: {source}</p>
<ul>
{items}
</ul>
</body>
</html>
"""


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--nodes", required=True, type=Path)
    parser.add_argument("--out-dir", type=Path, default=None)
    args = parser.parse_args()

    nodes_path = args.nodes if args.nodes.is_absolute() else REPO / args.nodes
    nodes = load_nodes(nodes_path)
    if not nodes:
        raise SystemExit(f"{nodes_path}: rỗng.")

    out_dir = args.out_dir or nodes_path.parent / "tree"
    out_dir = out_dir if out_dir.is_absolute() else REPO / out_dir
    out_dir.mkdir(parents=True, exist_ok=True)

    families = group_families(nodes)
    index_items = []
    for i, family in enumerate(families, start=1):
        title, body = render_family(family)
        slug = slugify(title)
        filename = f"{i:02d}-{slug}.html"
        page = PAGE_TEMPLATE.format(
            title=html.escape(title), css=CSS, source=nodes_path.name, count=len(family), body=body
        )
        (out_dir / filename).write_text(page, encoding="utf-8")
        index_items.append(f'<li><a href="{filename}">{html.escape(title)}</a> — {len(family)} người</li>')
        print(f"  wrote {(out_dir / filename).relative_to(REPO) if out_dir.is_relative_to(REPO) else out_dir / filename}")

    index_page = INDEX_TEMPLATE.format(
        title="Sơ đồ gia phả — danh sách gia đình",
        source=nodes_path.name,
        items="\n".join(index_items),
    )
    (out_dir / "index.html").write_text(index_page, encoding="utf-8")
    print(f"\n{len(families)} gia đình → {out_dir}/index.html")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
