"""Generate offline HTML viewers for review corpus."""

from __future__ import annotations

import html
import json
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from label_studio_pipeline.corpus_store import load_json

DEFAULT_CORPUS_DIR = Path("data/review_corpus")
DEFAULT_QUOC_NGU_DIR = Path("data/review_corpus/quoc_ngu")
DEFAULT_HANNOM_DIR = Path("data/review_corpus/hannom")
DEFAULT_SYNTHETIC_DIR = Path("data/synthetic_pha_ky")
DEFAULT_NOM_SOURCE_DIR = Path("data/hannom/nomfoundation/volumes")


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _read_text(path: Path) -> str:
    if not path.is_file():
        return ""
    return path.read_text(encoding="utf-8", errors="replace")


def _escape_pre(text: str) -> str:
    return html.escape(text)


def build_compare_html(*, tree_id: int, real_text: str, hybrid_text: str, meta: dict[str, Any]) -> str:
    lineage = html.escape(str(meta.get("lineage_name") or f"tree {tree_id}"))
    review = meta.get("review") if isinstance(meta.get("review"), dict) else {}
    stratum = html.escape(str(review.get("stratum") or ""))
    split = html.escape(str(review.get("split") or ""))
    real_block = _escape_pre(real_text)
    hybrid_block = _escape_pre(hybrid_text) if hybrid_text else "(chưa có bổ sung)"
    return f"""<!DOCTYPE html>
<html lang="vi">
<head>
  <meta charset="utf-8" />
  <title>Compare {tree_id} — {lineage}</title>
  <style>
    body {{ font-family: Georgia, "Times New Roman", serif; margin: 0; background: #f7f4ef; color: #222; }}
    header {{ background: #2f5d3a; color: #fff; padding: 1rem 1.25rem; }}
    header a {{ color: #dff3e4; }}
    .meta {{ font-size: 0.95rem; opacity: 0.95; margin-top: 0.35rem; }}
    .grid {{ display: grid; grid-template-columns: 1fr 1fr; gap: 0; min-height: calc(100vh - 88px); }}
    .pane {{ padding: 1rem 1.25rem; overflow: auto; }}
    .pane h2 {{ margin-top: 0; font-size: 1.05rem; color: #2f5d3a; }}
    .left {{ background: #fff; border-right: 1px solid #ddd; }}
    .right {{ background: #fffef8; }}
    pre {{ white-space: pre-wrap; word-break: break-word; line-height: 1.55; font-size: 0.98rem; }}
    .tag {{ display: inline-block; background: #e8f2ea; color: #2f5d3a; padding: 0.1rem 0.45rem; border-radius: 4px; margin-right: 0.35rem; }}
    @media (max-width: 900px) {{ .grid {{ grid-template-columns: 1fr; }} .left {{ border-right: none; border-bottom: 1px solid #ddd; }} }}
  </style>
</head>
<body>
  <header>
    <div><strong>tree_id {tree_id}</strong> — {lineage}</div>
    <div class="meta">
      <span class="tag">{stratum}</span>
      <span class="tag">{split}</span>
      <a href="../../index.html">← Tổng</a>
    </div>
  </header>
  <div class="grid">
    <section class="pane left">
      <h2>Phả ký thật (pha_ky.txt)</h2>
      <pre>{real_block}</pre>
    </section>
    <section class="pane right">
      <h2>Phả ký hybrid (thật + bổ sung sơ đồ)</h2>
      <pre>{hybrid_block}</pre>
    </section>
  </div>
</body>
</html>
"""


def build_index_html(*, trees: list[dict[str, Any]], hannom_volumes: list[dict[str, Any]]) -> str:
    rows = []
    for tree in sorted(trees, key=lambda item: int(item.get("tree_id") or 0)):
        tree_id = int(tree["tree_id"])
        review = tree.get("review") or {}
        lineage = html.escape(str(tree.get("lineage_name") or ""))
        stratum = html.escape(str(review.get("stratum") or ""))
        split = html.escape(str(review.get("split") or ""))
        has_synthetic = "✓" if tree.get("has_hybrid") else "—"
        image_count = int(tree.get("image_count") or 0)
        rows.append(
            f"<tr>"
            f"<td>{tree_id}</td>"
            f"<td>{lineage}</td>"
            f"<td>{stratum}</td>"
            f"<td>{split}</td>"
            f"<td>{image_count}</td>"
            f"<td>{has_synthetic}</td>"
            f'<td><a href="quoc_ngu/{tree_id}/compare.html">So sánh</a></td>'
            f"</tr>"
        )

    hannom_rows = []
    for vol in sorted(hannom_volumes, key=lambda item: int(item.get("volume_id") or 0)):
        volume_id = int(vol["volume_id"])
        title = html.escape(str(vol.get("title") or ""))
        pages = int(vol.get("page_count") or 0)
        hannom_rows.append(
            f"<tr>"
            f"<td>{volume_id}</td>"
            f"<td>{title}</td>"
            f"<td>{pages}</td>"
            f'<td><a href="hannom/{volume_id}/viewer.html">Xem</a></td>'
            f"</tr>"
        )

    return f"""<!DOCTYPE html>
<html lang="vi">
<head>
  <meta charset="utf-8" />
  <title>Review corpus</title>
  <style>
    body {{ font-family: system-ui, sans-serif; margin: 1.5rem; background: #fafafa; color: #222; }}
    h1, h2 {{ color: #2f5d3a; }}
    table {{ border-collapse: collapse; width: 100%; background: #fff; margin-bottom: 2rem; }}
    th, td {{ border: 1px solid #ddd; padding: 0.55rem 0.65rem; text-align: left; vertical-align: top; }}
    th {{ background: #e8f2ea; }}
    tr:nth-child(even) {{ background: #fcfcfc; }}
    a {{ color: #2f5d3a; }}
  </style>
</head>
<body>
  <h1>Review corpus</h1>
  <p>Generated {_now_iso()} · Quốc ngữ stratified + Hán-Nôm volumes · Hybrid = prose thật + bổ sung sơ đồ (v2).</p>

  <h2>Quốc ngữ — {len(trees)} cây</h2>
  <table>
    <thead>
      <tr>
        <th>tree_id</th><th>Dòng họ</th><th>Stratum</th><th>Split</th><th>Ảnh</th><th>Hybrid</th><th>Link</th>
      </tr>
    </thead>
    <tbody>
      {"".join(rows)}
    </tbody>
  </table>

  <h2>Hán-Nôm — {len(hannom_volumes)} volume</h2>
  <table>
    <thead>
      <tr><th>volume_id</th><th>Title</th><th>Trang</th><th>Link</th></tr>
    </thead>
    <tbody>
      {"".join(hannom_rows) if hannom_rows else '<tr><td colspan="4">(chưa có)</td></tr>'}
    </tbody>
  </table>
</body>
</html>
"""


def build_hannom_viewer_html(*, volume_id: int, title: str, pages: list[str]) -> str:
    safe_title = html.escape(title)
    if not pages:
        body = "<p>Chưa có ảnh trang.</p>"
    else:
        items = []
        for page in pages:
            items.append(f'<img src="pages/{html.escape(page)}" alt="{html.escape(page)}" loading="lazy" />')
        body = "\n".join(items)
    return f"""<!DOCTYPE html>
<html lang="vi">
<head>
  <meta charset="utf-8" />
  <title>Nom volume {volume_id} — {safe_title}</title>
  <style>
    body {{ font-family: system-ui, sans-serif; margin: 0; background: #111; color: #eee; }}
    header {{ padding: 0.75rem 1rem; background: #222; position: sticky; top: 0; }}
    header a {{ color: #9fd4aa; }}
    .pages {{ display: flex; flex-direction: column; align-items: center; gap: 1rem; padding: 1rem; }}
    img {{ max-width: min(100%, 980px); height: auto; background: #fff; }}
  </style>
</head>
<body>
  <header>
    <strong>volume {volume_id}</strong> — {safe_title}
    · <a href="../../index.html">← Tổng</a>
  </header>
  <div class="pages">
    {body}
  </div>
</body>
</html>
"""


def merge_synthetic_into_review(
    *,
    quoc_ngu_dir: Path,
    synthetic_dir: Path,
    tree_ids: list[int] | None = None,
) -> list[int]:
    merged: list[int] = []
    for tree_path in sorted(quoc_ngu_dir.iterdir(), key=lambda p: int(p.name) if p.name.isdigit() else 0):
        if not tree_path.is_dir() or not tree_path.name.isdigit():
            continue
        tree_id = int(tree_path.name)
        if tree_ids and tree_id not in tree_ids:
            continue
        src_base = synthetic_dir / str(tree_id)
        copied = False
        for src_name, dst_name in (
            ("pha_ky_supplement.txt", "pha_ky_supplement.txt"),
            ("pha_ky_hybrid.txt", "pha_ky_hybrid.txt"),
            ("synthetic_pha_ky.txt", "pha_ky_synthetic.txt"),
        ):
            src = src_base / src_name
            if src.is_file():
                shutil.copy2(src, tree_path / dst_name)
                copied = True
        if copied:
            merged.append(tree_id)
    return merged


def sync_hannom_volume(
    *,
    volume_id: int,
    source_dir: Path,
    hannom_dir: Path,
) -> dict[str, Any] | None:
    src = source_dir / str(volume_id)
    if not src.is_dir():
        return None
    dst = hannom_dir / str(volume_id)
    dst.mkdir(parents=True, exist_ok=True)

    for name in ("metadata.json", "manifest.json"):
        src_file = src / name
        if src_file.is_file():
            shutil.copy2(src_file, dst / name)

    src_pages = src / "pages"
    dst_pages = dst / "pages"
    if src_pages.is_dir():
        dst_pages.mkdir(parents=True, exist_ok=True)
        for page in sorted(src_pages.iterdir()):
            if page.is_file() and page.suffix.lower() in {".jpg", ".jpeg", ".png"}:
                target = dst_pages / page.name
                if not target.exists():
                    shutil.copy2(page, target)

    metadata = load_json(dst / "metadata.json") or load_json(src / "metadata.json") or {}
    manifest = load_json(dst / "manifest.json") or {}
    page_files = []
    if dst_pages.is_dir():
        page_files = sorted(p.name for p in dst_pages.iterdir() if p.is_file())
    elif isinstance(manifest.get("pages"), list):
        page_files = [p.get("filename") for p in manifest["pages"] if isinstance(p, dict) and p.get("filename")]

    title = metadata.get("title_vn") or metadata.get("title") or f"Volume {volume_id}"
    viewer_html = build_hannom_viewer_html(volume_id=volume_id, title=str(title), pages=page_files)
    (dst / "viewer.html").write_text(viewer_html, encoding="utf-8")

    return {
        "volume_id": volume_id,
        "title": title,
        "page_count": len(page_files),
        "export_dir": str(dst),
    }


def build_review_viewer(
    *,
    corpus_dir: Path = DEFAULT_CORPUS_DIR,
    quoc_ngu_dir: Path = DEFAULT_QUOC_NGU_DIR,
    hannom_dir: Path = DEFAULT_HANNOM_DIR,
    synthetic_dir: Path = DEFAULT_SYNTHETIC_DIR,
    nom_source_dir: Path = DEFAULT_NOM_SOURCE_DIR,
    merge_synthetic: bool = True,
) -> dict[str, Any]:
    quoc_ngu_dir.mkdir(parents=True, exist_ok=True)
    hannom_dir.mkdir(parents=True, exist_ok=True)

    index_data = load_json(quoc_ngu_dir / "index.json") or {}
    tree_ids = index_data.get("tree_ids")
    if not isinstance(tree_ids, list):
        tree_ids = [
            int(path.name)
            for path in quoc_ngu_dir.iterdir()
            if path.is_dir() and path.name.isdigit()
        ]

    merged_ids: list[int] = []
    if merge_synthetic and synthetic_dir.is_dir():
        merged_ids = merge_synthetic_into_review(
            quoc_ngu_dir=quoc_ngu_dir,
            synthetic_dir=synthetic_dir,
            tree_ids=[int(x) for x in tree_ids],
        )

    trees: list[dict[str, Any]] = []
    for tree_id in sorted(int(x) for x in tree_ids):
        tree_path = quoc_ngu_dir / str(tree_id)
        if not tree_path.is_dir():
            continue
        meta = load_json(tree_path / "meta.json") or {}
        real_text = _read_text(tree_path / "pha_ky.txt")
        hybrid_text = _read_text(tree_path / "pha_ky_hybrid.txt")
        if not hybrid_text.strip():
            real_only = real_text.strip()
            supplement = _read_text(tree_path / "pha_ky_supplement.txt")
            if supplement.strip() and real_only:
                from label_studio_pipeline.synthetic_pha_ky import build_hybrid_pha_ky

                hybrid_text = build_hybrid_pha_ky(real_only, supplement)
            elif supplement.strip():
                hybrid_text = supplement
        compare_html = build_compare_html(
            tree_id=tree_id,
            real_text=real_text,
            hybrid_text=hybrid_text,
            meta=meta,
        )
        (tree_path / "compare.html").write_text(compare_html, encoding="utf-8")

        images_meta = load_json(tree_path / "images.json") or {}
        trees.append(
            {
                "tree_id": tree_id,
                "lineage_name": meta.get("lineage_name"),
                "review": meta.get("review"),
                "has_hybrid": bool(hybrid_text.strip()) and hybrid_text.strip() != real_text.strip(),
                "image_count": images_meta.get("image_count") or 0,
            },
        )

    hannom_volumes: list[dict[str, Any]] = []
    if nom_source_dir.is_dir():
        for path in sorted(nom_source_dir.iterdir(), key=lambda p: int(p.name) if p.name.isdigit() else 0):
            if not path.is_dir() or not path.name.isdigit():
                continue
            synced = sync_hannom_volume(
                volume_id=int(path.name),
                source_dir=nom_source_dir,
                hannom_dir=hannom_dir,
            )
            if synced:
                hannom_volumes.append(synced)

    index_html = build_index_html(trees=trees, hannom_volumes=hannom_volumes)
    (corpus_dir / "index.html").write_text(index_html, encoding="utf-8")

    summary = {
        "corpus_dir": str(corpus_dir),
        "quoc_ngu_dir": str(quoc_ngu_dir),
        "hannom_dir": str(hannom_dir),
        "tree_count": len(trees),
        "synthetic_merged_count": len(merged_ids),
        "hannom_volume_count": len(hannom_volumes),
        "generated_at": _now_iso(),
    }
    (corpus_dir / "manifest.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return summary


def build_parser() -> argparse.ArgumentParser:
    import argparse

    parser = argparse.ArgumentParser(description="Build index.html + compare.html for review corpus.")
    parser.add_argument("--corpus-dir", type=Path, default=DEFAULT_CORPUS_DIR)
    parser.add_argument("--quoc-ngu-dir", type=Path, default=DEFAULT_QUOC_NGU_DIR)
    parser.add_argument("--hannom-dir", type=Path, default=DEFAULT_HANNOM_DIR)
    parser.add_argument("--synthetic-dir", type=Path, default=DEFAULT_SYNTHETIC_DIR)
    parser.add_argument("--nom-source-dir", type=Path, default=DEFAULT_NOM_SOURCE_DIR)
    parser.add_argument(
        "--no-merge-synthetic",
        action="store_true",
        help="Do not copy synthetic_pha_ky.txt into review tree folders.",
    )
    return parser


def main() -> None:
    import json
    import sys

    args = build_parser().parse_args()
    summary = build_review_viewer(
        corpus_dir=args.corpus_dir,
        quoc_ngu_dir=args.quoc_ngu_dir,
        hannom_dir=args.hannom_dir,
        synthetic_dir=args.synthetic_dir,
        nom_source_dir=args.nom_source_dir,
        merge_synthetic=not args.no_merge_synthetic,
    )
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
