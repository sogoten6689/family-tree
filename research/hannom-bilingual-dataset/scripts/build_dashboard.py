#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Sinh dashboard/status.json + dashboard/index.html từ dữ liệu đã có sẵn.

Chỉ ĐỌC (data/track*/*.json + manifest/classification.json) — KHÔNG gọi
OCR/API nào. Chạy lại bất cứ lúc nào để cập nhật dashboard sau khi có phân
loại/OCR/dịch mới.

Dùng:
  python3 scripts/build_dashboard.py

Xem dashboard/FEATURE.md để biết cấu trúc dữ liệu + thiết kế giao diện.
"""
from __future__ import annotations

import glob
import html
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from rapidfuzz.distance import Levenshtein

from _repo_paths import DATA_REPO_ROOT

ROOT = Path(__file__).resolve().parents[1]

GROUP_NAMES = {
    1: "Hán Nôm thô",
    2: "Hán Nôm đã dịch (chưa dóng hàng)",
    3: "Tiếng Việt hiện đại",
}

ENGINE_LABELS = {
    "kim_hannom_lab": "Kim Hán Nôm Lab",
    "paddle_v6": "Paddle v6",
    "deepseek": "DeepSeek",
    "google_vision": "Google Vision",
    "gemini": "Gemini",
}

ENGINE_ORDER = list(ENGINE_LABELS)

SPAN_METHOD_LABELS = {
    "line_unanimous": ("Thống nhất", "Mọi engine cùng 1 dòng — không ghi đè."),
    "line_majority_override": ("Ghi đè backbone", "Cụm khác backbone có nhiều phiếu hơn → chọn nguyên dòng thắng."),
    "line_confirmed_majority": ("Giữ backbone (đa số)", "Backbone thắng đa số thật; fallback vị trí nếu còn lệch ký tự."),
    "line_no_majority": ("Hoà phiếu", "Không cụm nào áp đảo → giữ backbone; fallback vote từng vị trí (≥3 engine đồng thuận mới sửa)."),
    "majority_override": ("Ghi đè (vote ký tự cũ)", "Đa số ký tự khác backbone."),
    "confirmed_majority": ("Giữ backbone (ký tự cũ)", "Backbone được đa số xác nhận."),
    "flagged_no_majority": ("Hoà (ký tự cũ)", "Không đủ đa số — giữ backbone."),
}

_VOTE_LINE = re.compile(
    r"^(.+)_backbone_line_vote_levenshtein_(\d+)_other(?:_excl_(.+)_for_odd)?$"
)
_VOTE_CHAR = re.compile(
    r"^(.+)_backbone_char_vote_(\d+)_other(?:_excl_(.+)_for_odd)?$"
)
_VOTE_ONLY = re.compile(
    r"^(.+)_only_no_other_engine(?:_excl_(.+)_for_odd)?$"
)


def engine_label(name: str | None) -> str:
    if not name:
        return "—"
    return ENGINE_LABELS.get(name, name)


def parse_vote_method(raw: str | None) -> dict[str, Any]:
    """Tách chuỗi vote_method thành backbone / số phiếu / engine bị loại."""
    empty = {
        "raw": raw, "algo": None, "backbone": None, "n_other": None,
        "excluded": None, "label": "Chưa vote",
    }
    if not raw:
        return empty
    m = _VOTE_LINE.match(raw)
    if m:
        bb, n, excl = m.group(1), int(m.group(2)), m.group(3)
        bits = [f"Backbone {engine_label(bb)}", f"vote câu/Levenshtein với {n} engine khác"]
        if excl:
            bits.append(f"loại {engine_label(excl)} để số phiếu lẻ")
        return {"raw": raw, "algo": "line", "backbone": bb, "n_other": n,
                "excluded": excl, "label": " · ".join(bits)}
    m = _VOTE_CHAR.match(raw)
    if m:
        bb, n, excl = m.group(1), int(m.group(2)), m.group(3)
        bits = [f"Backbone {engine_label(bb)}", f"vote ký tự cũ với {n} engine khác"]
        if excl:
            bits.append(f"loại {engine_label(excl)} để số phiếu lẻ")
        return {"raw": raw, "algo": "char", "backbone": bb, "n_other": n,
                "excluded": excl, "label": " · ".join(bits)}
    m = _VOTE_ONLY.match(raw)
    if m:
        bb, excl = m.group(1), m.group(2)
        bits = [f"Chỉ {engine_label(bb)} bỏ phiếu"]
        if excl:
            bits.append(f"loại {engine_label(excl)} vì chỉ còn 2 engine (giữ số lẻ)")
        else:
            bits.append("không engine khác có dữ liệu")
        return {"raw": raw, "algo": "only", "backbone": bb, "n_other": 0,
                "excluded": excl, "label": " · ".join(bits)}
    return {**empty, "label": raw, "algo": "unknown"}


def chosen_source(voted_text: str | None, engines: dict[str, Any]) -> str | None:
    if not voted_text:
        return None
    for name, meta in engines.items():
        text = meta.get("text") if isinstance(meta, dict) else meta
        if text == voted_text:
            return name
    return None


def load_records() -> list[dict[str, Any]]:
    docs = []
    for f in sorted(glob.glob(str(DATA_REPO_ROOT / "data/*/*.json"))):
        docs.append(json.loads(Path(f).read_text(encoding="utf-8")))
    return docs


def build_doc_entry(d: dict[str, Any]) -> dict[str, Any]:
    pages_out = []
    total = len(d.get("pages", []))
    n_l1 = n_l2 = n_l3 = 0
    engines_used: set[str] = set()
    rates = []
    algo_counts: dict[str, int] = {}
    backbone_counts: dict[str, int] = {}
    n_override = 0
    for p in d.get("pages", []):
        l1 = p.get("l1_ocr") or {}
        voted_text = l1.get("voted_text")
        if voted_text:
            n_l1 += 1
        engines_raw = l1.get("engines") or {}
        engines_used.update(engines_raw.keys())
        engines = {
            name: {
                "text": e.get("text") if isinstance(e, dict) else e,
                "score": e.get("score") if isinstance(e, dict) else None,
                "similarity_to_others": e.get("similarity_to_others") if isinstance(e, dict) else None,
            }
            for name, e in engines_raw.items()
        }
        parsed = parse_vote_method(l1.get("vote_method"))
        if parsed["algo"]:
            algo_counts[parsed["algo"]] = algo_counts.get(parsed["algo"], 0) + 1
        if parsed["backbone"]:
            backbone_counts[parsed["backbone"]] = backbone_counts.get(parsed["backbone"], 0) + 1
        spans = l1.get("uncertain_spans") or []
        spans_out = []
        for s in spans:
            item = {k: s[k] for k in (
                "line", "voted_line", "method", "n_agree", "n_total",
                "disagreeing", "resolved", "pos", "votes",
            ) if k in s}
            pos = s.get("positional")
            if isinstance(pos, dict):
                # XÁC NHẬN 2026-09-21: giữ ĐẦY ĐỦ uncertain_positions (trước chỉ
                # giữ 1 con số) — cần chi tiết engine nào bỏ phiếu ký tự gì ở
                # từng vị trí để hiển thị "vote từng chữ" trên dashboard.
                item["positional"] = pos
            spans_out.append(item)
        n_override += sum(1 for s in spans if s.get("method") == "line_majority_override")
        if l1.get("uncertain_rate") is not None:
            rates.append(l1["uncertain_rate"])
        if p.get("l2_phien_am"):
            n_l2 += 1
        if p.get("l3_dich_nghia"):
            n_l3 += 1
        pages_out.append({
            "page_id": p["page_id"],
            "l0_image": p.get("l0_image"),
            "engines": engines,
            "voted_text": voted_text,
            "vote_method": l1.get("vote_method"),
            "vote": parsed,
            "chosen_engine": chosen_source(voted_text, engines),
            "uncertain_spans": spans_out,
            "uncertain_rate": l1.get("uncertain_rate"),
            "l2_phien_am": p.get("l2_phien_am"),
            "l3_dich_nghia": p.get("l3_dich_nghia"),
            "pairs": p.get("pairs") or [],
        })
    avg_rate = (sum(rates) / len(rates)) if rates else None
    return {
        "doc_id": d["doc_id"],
        "ma_dinh_danh": d.get("ma_dinh_danh"),
        "group": d["track"],
        "title_han": d.get("ten_goc_han"),
        "title_vn": d.get("ten_han_viet"),
        "ho": d.get("ho"),
        "quy_mo": d.get("quy_mo"),
        "hinh_thuc": d.get("hinh_thuc"),
        "dia_danh": d.get("dia_danh"),
        "nien_dai": d.get("nien_dai"),
        "status": d.get("status"),
        "ghi_chu": d.get("ghi_chu"),
        "stats": {
            "total_pages": total,
            "pages_l1": n_l1,
            "pages_l2": n_l2,
            "pages_l3": n_l3,
            "engines_used": sorted(engines_used),
            "avg_uncertain_rate": avg_rate,
            "vote_algo_counts": algo_counts,
            "backbone_counts": backbone_counts,
            "n_majority_override_lines": n_override,
        },
        "pages": pages_out,
    }


def build_data(raw_docs: list[dict[str, Any]]) -> dict[str, Any]:
    entries = [build_doc_entry(d) for d in raw_docs]
    entries.sort(key=lambda e: (e["group"], e["doc_id"]))

    by_group: dict[int, int] = {}
    for e in entries:
        by_group[e["group"]] = by_group.get(e["group"], 0) + 1

    def all_pages_done(e: dict[str, Any], key: str) -> bool:
        return e["stats"]["total_pages"] > 0 and e["stats"][key] == e["stats"]["total_pages"]

    overall = {
        "total_docs": len(entries),
        "by_group": {str(k): v for k, v in sorted(by_group.items())},
        "group_names": {str(k): v for k, v in GROUP_NAMES.items()},
        "with_ma_dinh_danh": sum(1 for e in entries if e["ma_dinh_danh"]),
        "l1_done_docs": sum(1 for e in entries if all_pages_done(e, "pages_l1")),
        "l2_done_docs": sum(1 for e in entries if all_pages_done(e, "pages_l2")),
        "l3_done_docs": sum(1 for e in entries if all_pages_done(e, "pages_l3")),
        "pages_vote_line": sum(e["stats"]["vote_algo_counts"].get("line", 0) for e in entries),
        "pages_vote_only": sum(e["stats"]["vote_algo_counts"].get("only", 0) for e in entries),
        "pages_vote_char": sum(e["stats"]["vote_algo_counts"].get("char", 0) for e in entries),
        "n_majority_override_lines": sum(e["stats"]["n_majority_override_lines"] for e in entries),
    }
    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "overall_stats": overall,
        "documents": entries,
    }


# ---------- render HTML (server-side, không cần JS để hiển thị) ----------

def esc(s: Any) -> str:
    if s is None:
        return ""
    return html.escape(str(s))


def status_badge(status: str | None) -> str:
    colors = {
        "draft": ("var(--sub-bg)", "var(--sub)"),
        "l1_done": ("var(--blue-bg)", "var(--blue)"),
        "l2_done": ("var(--purple-bg)", "var(--purple)"),
        "l3_done": ("var(--green-bg)", "var(--green)"),
        "reviewed": ("var(--green-bg)", "var(--green)"),
        "final": ("var(--green-bg)", "var(--green)"),
    }
    bg, fg = colors.get(status or "draft", ("var(--sub-bg)", "var(--sub)"))
    return f'<span class="badge" style="background:{bg};color:{fg}">{esc(status or "draft")}</span>'


def ordered_engines(engines: dict[str, Any]) -> list[tuple[str, dict[str, Any]]]:
    out: list[tuple[str, dict[str, Any]]] = []
    seen: set[str] = set()
    for name in ENGINE_ORDER:
        if name in engines:
            out.append((name, engines[name]))
            seen.add(name)
    for name, meta in engines.items():
        if name not in seen:
            out.append((name, meta if isinstance(meta, dict) else {"text": meta}))
    return out


# ---------- vote từng chữ (character-level, dựng ngay lúc build bằng Python —
# tránh lệch chỉ số codepoint/UTF-16 vốn chỉ xảy ra khi làm việc này ở JS,
# xem bài học từ artifact "Sổ Khảo Dị OCR" 2026-09-15) ----------

def char_diff_spans(voted: str, other: str) -> str:
    """HTML tô màu `other` theo phép biến đổi Levenshtein THẬT so với `voted`:
    equal = giữ nguyên màu chữ thường, replace = đỏ (chữ bị thay), insert =
    vàng (chữ thừa, other có mà voted không có), delete = chấm mờ thay chỗ
    trống (chữ other bị thiếu so với voted)."""
    parts: list[str] = []
    for op in Levenshtein.opcodes(voted, other):
        seg = other[op.dest_start:op.dest_end]
        if op.tag == "equal":
            parts.append(f'<span class="ch-eq">{esc(seg)}</span>')
        elif op.tag == "replace":
            parts.append(f'<span class="ch-rep">{esc(seg)}</span>')
        elif op.tag == "insert":
            parts.append(f'<span class="ch-ins">{esc(seg)}</span>')
        elif op.tag == "delete":
            parts.append(f'<span class="ch-gap">{"·" * (op.src_end - op.src_start)}</span>')
    return "".join(parts)


def voted_line_contested_html(voted: str, disagreeing: list[dict[str, Any]]) -> str:
    """Câu thắng cuộc, gạch chân đỏ ở mọi vị trí có ≥1 engine đọc khác đi."""
    if not voted:
        return ""
    mask = [False] * len(voted)
    for d in disagreeing:
        other = d.get("text") or ""
        for op in Levenshtein.opcodes(voted, other):
            if op.tag != "equal":
                for i in range(op.src_start, min(op.src_end, len(mask))):
                    mask[i] = True
    return "".join(
        f'<span class="ch-contested">{esc(ch)}</span>' if mask[i] else esc(ch)
        for i, ch in enumerate(voted)
    )


def render_positional(pos: dict[str, Any]) -> str:
    """Chi tiết fallback vote từng VỊ TRÍ ký tự (vote_line_positional trong
    vote_ocr.py) — trước đây dashboard chỉ hiện 1 con số, giờ hiện đúng engine
    nào bỏ phiếu ký tự gì ở từng vị trí/khe hở."""
    positions = pos.get("uncertain_positions") or []
    if not positions:
        return ""
    rows = []
    for up in positions:
        if "backbone_pos" in up:
            label = f'Vị trí {up.get("backbone_pos")} (gốc "{esc(up.get("backbone_char") or "")}")'
        else:
            label = f'Khe trước vị trí {up.get("gap_before")} (chữ chèn thêm, lượt {up.get("insert_index", 0) + 1})'
        resolved = up.get("resolved")
        votes = up.get("votes") or {}
        vote_bits = []
        for val, engines in votes.items():
            if val == "__keep__":
                shown = "giữ nguyên backbone"
            elif val in ("__delete__", ""):
                shown = "bỏ (không có chữ)"
            else:
                shown = f'"{esc(val)}"'
            vote_bits.append(f'{shown}: {", ".join(engine_label(n) for n in engines)}')
        cls = "pos-fixed" if resolved else "pos-open"
        outcome = (
            f'→ sửa thành <span class="ch-rep">{esc(resolved)}</span>'
            if resolved else '<i>giữ nguyên (chưa đủ ≥3 engine đồng thuận)</i>'
        )
        rows.append(
            f'<div class="pos-row {cls}"><b>{esc(label)}</b> {outcome}'
            f'<div class="pos-votes">{" · ".join(vote_bits)}</div></div>'
        )
    return f'<div class="positions">{"".join(rows)}</div>'


def render_spans(spans: list[dict[str, Any]]) -> str:
    if not spans:
        return '<div class="empty">Không có dòng bất đồng (unanimous, hoặc chỉ 1 engine được phép bỏ phiếu)</div>'
    cards = []
    cls_map = {
        "line_majority_override": "span-override",
        "line_no_majority": "span-tie",
        "line_confirmed_majority": "span-keep",
        "line_unanimous": "span-ok",
    }
    for s in spans:
        method = s.get("method") or "?"
        title, hint = SPAN_METHOD_LABELS.get(method, (method, ""))
        n_a, n_t = s.get("n_agree"), s.get("n_total")
        vote_frac = f"{n_a}/{n_t}" if n_a is not None else "—"
        voted_line = s.get("voted_line") or s.get("resolved") or ""
        disagreeing = s.get("disagreeing") or []
        # Vote TỪNG CHỮ: tô màu ký tự khác nhau (Levenshtein thật) thay vì in
        # nguyên văn không tô màu — XÁC NHẬN 2026-09-21, theo yêu cầu bổ sung
        # phân tích từng chữ trên dashboard (trước đó chỉ có ở artifact riêng).
        disag_html = "".join(
            f'<li><b>{esc(engine_label(d.get("engine")))}</b> · sim {d.get("similarity")}'
            f'<pre class="han-diff">{char_diff_spans(voted_line, d.get("text") or "")}</pre></li>'
            for d in disagreeing
        ) or "<li>không có</li>"
        pos = s.get("positional") or {}
        pos_html = render_positional(pos) if pos else ""
        voted_marked = voted_line_contested_html(voted_line, disagreeing)
        cards.append(
            f'<div class="span-card {cls_map.get(method, "")}">'
            f'<div class="span-head">Dòng {s.get("line")} · '
            f'<span class="span-method">{esc(title)}</span> · phiếu thắng {esc(vote_frac)}</div>'
            f'<div class="span-hint">{esc(hint)}</div>'
            f'<pre class="span-voted han-diff">{voted_marked}</pre>'
            f'<div class="field-label">Engine không theo cụm thắng — tô màu: đỏ=bị thay, vàng=chữ thừa, chấm mờ=chữ thiếu</div>'
            f'<ul class="span-dis">{disag_html}</ul>'
            f'{pos_html}</div>'
        )
    return f'<div class="spans">{"".join(cards)}</div>'


def render_page(p: dict[str, Any]) -> str:
    rate = p["uncertain_rate"]
    rate_txt = f"{rate * 100:.1f}%" if rate is not None else "-"
    vote = p.get("vote") or parse_vote_method(p.get("vote_method"))
    backbone = vote.get("backbone")
    excluded = vote.get("excluded")
    chosen = p.get("chosen_engine")
    n_spans = len(p.get("uncertain_spans") or [])

    engine_blocks = []
    for name, meta in ordered_engines(p["engines"]):
        if not isinstance(meta, dict):
            meta = {"text": meta}
        tags = []
        classes = ["engine-block"]
        if name == backbone:
            tags.append('<span class="etag etag-bb">backbone</span>')
            classes.append("is-backbone")
        if name == excluded:
            tags.append('<span class="etag etag-ex">loại (phiếu lẻ)</span>')
            classes.append("is-excluded")
        if name == chosen:
            tags.append('<span class="etag etag-win">trùng kết quả cả trang</span>')
            classes.append("is-winner")
        sim = meta.get("similarity_to_others")
        sim_txt = f"sim vs khác {sim:.3f}" if isinstance(sim, (int, float)) else "sim —"
        engine_blocks.append(
            f'<div class="{" ".join(classes)}">'
            f'<div class="engine-name">{esc(engine_label(name))} {" ".join(tags)}</div>'
            f'<div class="engine-meta">{esc(sim_txt)}</div>'
            f'<pre>{esc(meta.get("text") or "")}</pre></div>'
        )
    engines_html = "".join(engine_blocks) or '<div class="empty">Chưa có engine nào OCR trang này</div>'

    if p["voted_text"]:
        if chosen:
            pick = f"Kết quả cả trang trùng nguyên text của {engine_label(chosen)}."
        else:
            pick = "Kết quả mix theo dòng (không trùng nguyên văn 1 engine)."
        voted = (
            f'<div class="vote-pick">{esc(pick)}</div>'
            f'<pre class="voted">{esc(p["voted_text"])}</pre>'
        )
    else:
        voted = '<div class="empty">Chưa vote</div>'

    l2 = f'<pre>{esc(p["l2_phien_am"])}</pre>' if p["l2_phien_am"] else '<div class="empty">Chưa phiên âm</div>'
    l3 = f'<pre>{esc(p["l3_dich_nghia"])}</pre>' if p["l3_dich_nghia"] else '<div class="empty">Chưa dịch nghĩa</div>'
    n_pairs = len(p["pairs"])

    if p["pairs"]:
        pair_rows = "".join(
            f'<div class="pair-row"><div class="pair-han">{esc(pr.get("han"))}</div>'
            f'<div class="pair-arrow">↔</div>'
            f'<div class="pair-viet">{esc(pr.get("viet"))}'
            f'<span class="pair-conf conf-{esc(pr.get("confidence") or "trung_binh")}">{esc(pr.get("confidence") or "-")}</span></div></div>'
            for pr in p["pairs"]
        )
        pairs_html = f'<div class="pairs-list">{pair_rows}</div>'
    else:
        pairs_html = '<div class="empty">Chưa ghép cặp nào</div>'

    return f"""
    <details class="page-detail">
      <summary>Trang {esc(p['page_id'])} — {len(p['engines'])} engine · {esc(vote.get("label") or "chưa vote")} · unc. {rate_txt} · {n_spans} dòng bất đồng</summary>
      <div class="page-body">
        <div class="vote-box">
          <div class="field-label">Cách chọn trang này</div>
          <div>{esc(vote.get("label") or "Chưa vote")}</div>
          <code class="vote-raw">{esc(vote.get("raw") or "—")}</code>
        </div>

        <div class="field-label">Ảnh gốc</div>
        <div class="empty">{esc(p['l0_image']) or '(không có)'}</div>

        <div class="field-label">OCR từng engine (backbone / loại phiếu lẻ / trùng kết quả)</div>
        <div class="engines-grid">{engines_html}</div>

        <div class="field-label">Kết quả sau vote (L1)</div>
        {voted}

        <div class="field-label">Dòng bất đồng — {n_spans} dòng</div>
        {render_spans(p.get("uncertain_spans") or [])}

        <div class="field-label">Phiên âm Hán-Việt (L2)</div>
        {l2}

        <div class="field-label">Dịch nghĩa (L3)</div>
        {l3}

        <div class="field-label">Cặp Hán-Việt đã ghép (pairs) — {n_pairs} cặp</div>
        {pairs_html}
      </div>
    </details>"""


def _vote_pill(algo: dict[str, int]) -> str:
    if algo.get("line") and not algo.get("char") and not algo.get("only"):
        return "vote câu"
    if algo.get("only") and not algo.get("line") and not algo.get("char"):
        return "1 phiếu lẻ"
    if algo.get("char") and not algo.get("line"):
        return "vote ký tự cũ"
    if algo:
        return "vote hỗn hợp"
    return "chưa vote"


def render_doc_summary(e: dict[str, Any]) -> str:
    """Chỉ phần <summary> + khung rỗng cho thân trang — KHÔNG chứa nội dung
    từng trang (text OCR, dòng bất đồng...). Thân trang được JS tải riêng từ
    `data/<doc_id>.html` khi người xem thật sự mở tài liệu đó (lazy load) —
    XÁC NHẬN 2026-09-21: đây là phần sửa chính cho việc dashboard bị lag, vì
    trước đó TOÀN BỘ nội dung mọi tài liệu được nhúng thẳng vào 1 file HTML
    (111MB) dù người xem chỉ cần 1 tài liệu."""
    s = e["stats"]
    rate = s["avg_uncertain_rate"]
    rate_txt = f"{rate * 100:.1f}%" if rate is not None else "-"
    ma = e["ma_dinh_danh"] or "—"
    ma_class = "ma-yes" if e["ma_dinh_danh"] else "ma-no"
    vote_pill = _vote_pill(s.get("vote_algo_counts") or {})
    bb_counts = s.get("backbone_counts") or {}
    bb_name = max(bb_counts, key=bb_counts.get) if bb_counts else None
    bb_pill = f"bb {engine_label(bb_name)}" if bb_name else "bb —"
    ov = s.get("n_majority_override_lines") or 0
    doc_id = esc(e["doc_id"])

    return f"""
  <details class="doc-detail" data-doc-id="{doc_id}">
    <summary>
      <span class="doc-id">{doc_id}</span>
      <span class="doc-title">{esc(e['title_vn']) or '(chưa đặt tên)'}</span>
      <span class="ma-dinh-danh {ma_class}">{esc(ma)}</span>
      {status_badge(e['status'])}
      <span class="pill">{s['pages_l1']}/{s['total_pages']} L1</span>
      <span class="pill">{s['pages_l2']}/{s['total_pages']} L2</span>
      <span class="pill">{s['pages_l3']}/{s['total_pages']} L3</span>
      <span class="pill vote">{esc(vote_pill)}</span>
      <span class="pill">{esc(bb_pill)}</span>
      <span class="pill">ghi đè {ov} dòng</span>
      <span class="pill rate">unc. {rate_txt}</span>
      <button type="button" class="json-btn" data-doc="{doc_id}" onclick="event.preventDefault(); openJsonPanel('{doc_id}')">{{ }} JSON</button>
    </summary>
    <div class="doc-body" id="body-{doc_id}"><div class="empty">Đang tải…</div></div>
  </details>"""


def render_doc_body(e: dict[str, Any]) -> str:
    """Nội dung đầy đủ 1 tài liệu (bảng meta + từng trang) — ghi ra
    `dashboard/data/<doc_id>.html`, KHÔNG còn nằm trong index.html."""
    s = e["stats"]
    meta_rows = "".join(
        f'<tr><td>{esc(label)}</td><td>{esc(val) if val else "<i>chưa có</i>"}</td></tr>'
        for label, val in [
            ("Tên Hán", e["title_han"]), ("Tên Hán-Việt", e["title_vn"]),
            ("Họ", e["ho"]), ("Quy mô", e["quy_mo"]), ("Hình thức", e["hinh_thuc"]),
            ("Địa danh", e["dia_danh"]), ("Niên đại", e["nien_dai"]),
            ("Ghi chú", e["ghi_chu"]),
        ]
    )
    pages_html = "".join(render_page(p) for p in e["pages"]) or '<div class="empty">Chưa có trang nào</div>'
    bb_counts = s.get("backbone_counts") or {}
    return (
        f'<table class="meta-table">{meta_rows}</table>'
        f'<div class="engines-used">Engine đã dùng: {", ".join(engine_label(x) for x in s["engines_used"]) or "chưa có"}'
        f' · backbone theo trang: {", ".join(f"{engine_label(k)} ×{v}" for k, v in sorted(bb_counts.items(), key=lambda kv: -kv[1])) or "—"}</div>'
        f'{pages_html}'
    )


def render_group(group_id: int, name: str, docs: list[dict[str, Any]]) -> str:
    if not docs:
        return ""
    body = "".join(render_doc_summary(e) for e in docs)
    return f"""
<section class="group">
  <h2>Nhóm {group_id} — {esc(name)} <span class="count">({len(docs)})</span></h2>
  {body}
</section>"""


def render_html(data: dict[str, Any]) -> str:
    o = data["overall_stats"]
    stat_cards = "".join(
        f'<div class="stat-card"><div class="stat-num">{v}</div><div class="stat-label">{esc(k)}</div></div>'
        for k, v in [
            ("Tổng tài liệu", o["total_docs"]),
            ("Có mã định danh", o["with_ma_dinh_danh"]),
            ("Đã OCR+vote đủ (L1)", o["l1_done_docs"]),
            ("Đã phiên âm đủ (L2)", o["l2_done_docs"]),
            ("Đã dịch nghĩa đủ (L3)", o["l3_done_docs"]),
            ("Trang vote câu", o.get("pages_vote_line", 0)),
            ("Trang 1 phiếu", o.get("pages_vote_only", 0)),
            ("Dòng ghi đè backbone", o.get("n_majority_override_lines", 0)),
        ]
    )
    legend = """
  <details class="legend" open>
    <summary>Cách vote L1 — đọc trước khi xem từng trang</summary>
    <ol>
      <li><b>Backbone</b> = engine giống các engine khác nhất trên trang (bag-of-lines), không còn thứ tự ưu tiên cố định.</li>
      <li>Nếu số engine <i>khác</i> backbone là <b>lẻ</b> (tổng phiếu chẵn) → loại 1 engine giống kém nhất, giữ số phiếu lẻ. Engine bị loại vẫn hiện text, không bỏ phiếu.</li>
      <li>Đúng 2 engine: loại nốt engine thứ hai → chỉ backbone bỏ phiếu. <code>uncertain_rate</code> = 0% là đúng thiết kế, không phải “OCR hoàn hảo”.</li>
      <li>Từng dòng: gom cụm Levenshtein ≥ 0.92. Cụm khác backbone có <b>nhiều phiếu hơn</b> mới ghi đè cả dòng (<span class="span-method">Ghi đè backbone</span>).</li>
      <li>Hoà phiếu / chỉ backbone tự xác nhận → fallback vote từng vị trí; chỉ sửa khi ≥ 3 engine đồng thuận đúng 1 chỗ.</li>
      <li><code>uncertain_rate</code> = số dòng bất đồng / số dòng backbone — không so với bản vote ký tự cũ.</li>
    </ol>
  </details>
"""
    groups_html = "".join(
        render_group(gid, o["group_names"][str(gid)],
                     [e for e in data["documents"] if e["group"] == gid])
        for gid in (1, 2, 3)
    )
    gen_at = data["generated_at"]

    return f"""<!DOCTYPE html>
<html lang="vi">
<head>
<meta charset="UTF-8">
<title>Dashboard — hannom-bilingual-dataset</title>
<style>
{CSS}
</style>
</head>
<body>
  <h1>Dashboard dữ liệu Hán Nôm</h1>
  <div class="subtitle">Sinh lúc {esc(gen_at)} — chạy <code>python3 scripts/build_dashboard.py</code> để cập nhật.
    Nội dung từng tài liệu tải riêng khi mở (<code>data/&lt;doc_id&gt;.html</code>) — cần chạy qua server tĩnh
    (vd. <code>python3 -m http.server</code> trong thư mục <code>dashboard/</code>), mở trực tiếp bằng
    file:// sẽ không tải được do trình duyệt chặn fetch() nội bộ.</div>

  <div class="stats-row">{stat_cards}</div>
  {legend}

  {groups_html}

  <div id="json-panel" class="json-panel">
    <div class="json-panel-header">
      <span id="json-panel-title">—</span>
      <button type="button" class="json-panel-close" onclick="closeJsonPanel()">✕ Đóng</button>
    </div>
    <pre id="json-panel-content"></pre>
  </div>
  <div id="json-panel-overlay" class="json-panel-overlay" onclick="closeJsonPanel()"></div>

  <script>
{JS}
  </script>
</body>
</html>"""


CSS = """
:root {
  --bg: #0f1420; --card: #161d2e; --card2: #1b2338; --border: #262f45;
  --text: #eef1f8; --sub: #9aa5bd; --sub-bg: rgba(154,165,189,0.12);
  --green: #34d399; --green-bg: rgba(52,211,153,0.12);
  --amber: #fbbf24; --amber-bg: rgba(251,191,36,0.10);
  --blue: #60a5fa; --blue-bg: rgba(96,165,250,0.12);
  --purple: #c084fc; --purple-bg: rgba(192,132,252,0.12);
  --red: #f87171; --red-bg: rgba(248,113,113,0.12);
}
@media (prefers-color-scheme: light) {
  :root {
    --bg: #f4f6fb; --card: #ffffff; --card2: #f8f9fd; --border: #e2e6f0;
    --text: #1a2033; --sub: #626e88; --sub-bg: rgba(98,110,136,0.08);
    --green: #0f9d68; --green-bg: rgba(15,157,104,0.08);
    --amber: #b8860b; --amber-bg: rgba(184,134,11,0.08);
    --blue: #2563eb; --blue-bg: rgba(37,99,235,0.08);
    --purple: #9333ea; --purple-bg: rgba(147,51,234,0.08);
    --red: #dc2626; --red-bg: rgba(220,38,38,0.08);
  }
}
* { box-sizing: border-box; }
body {
  margin: 0; background: var(--bg); color: var(--text);
  font-family: -apple-system, "Segoe UI", "Helvetica Neue", Arial, sans-serif;
  padding: 32px 40px; max-width: 1400px; margin: 0 auto;
}
h1 { font-size: 24px; margin: 0 0 4px; }
.subtitle { color: var(--sub); font-size: 13px; margin-bottom: 24px; }
.subtitle code { background: var(--card2); padding: 1px 6px; border-radius: 4px; }

.stats-row { display: grid; grid-template-columns: repeat(4, 1fr); gap: 12px; margin-bottom: 16px; }
.stat-card { background: var(--card); border: 1px solid var(--border); border-radius: 12px; padding: 14px 16px; text-align: center; }
.stat-num { font-size: 26px; font-weight: 800; }
.stat-label { font-size: 11.5px; color: var(--sub); margin-top: 2px; }

.group { margin-bottom: 28px; }
.group h2 { font-size: 17px; border-bottom: 2px solid var(--border); padding-bottom: 8px; }
.group h2 .count { color: var(--sub); font-weight: 400; font-size: 14px; }

details.doc-detail {
  background: var(--card); border: 1px solid var(--border); border-radius: 10px;
  margin-bottom: 8px; padding: 10px 14px;
}
details.doc-detail > summary {
  cursor: pointer; display: flex; align-items: center; gap: 10px; flex-wrap: wrap;
  list-style: none; font-size: 13.5px;
}
details.doc-detail > summary::-webkit-details-marker { display: none; }
details.doc-detail > summary::before { content: "▸"; color: var(--sub); }
details.doc-detail[open] > summary::before { content: "▾"; }
.doc-id { font-family: "SF Mono", Menlo, monospace; font-weight: 700; }
.doc-title { color: var(--sub); flex-grow: 1; }
.ma-dinh-danh { font-family: "SF Mono", Menlo, monospace; font-size: 11.5px; padding: 2px 8px; border-radius: 6px; }
.ma-yes { background: var(--green-bg); color: var(--green); }
.ma-no { background: var(--sub-bg); color: var(--sub); }
.badge { font-size: 11px; font-weight: 700; padding: 2px 9px; border-radius: 999px; }
.pill { font-size: 11px; background: var(--card2); border: 1px solid var(--border); padding: 2px 8px; border-radius: 999px; color: var(--sub); }
.pill.rate { color: var(--amber); }
.pill.vote { color: var(--blue); border-color: var(--blue); }

.legend {
  background: var(--card); border: 1px solid var(--border); border-radius: 12px;
  padding: 10px 16px; margin-bottom: 28px; font-size: 13.5px; line-height: 1.55;
}
.legend > summary { cursor: pointer; font-weight: 700; }
.legend ol { margin: 8px 0 4px; padding-left: 22px; color: var(--text); }
.legend code { background: var(--card2); padding: 1px 6px; border-radius: 4px; font-size: 12px; }

.vote-box {
  background: var(--blue-bg); border: 1px solid var(--blue); border-radius: 8px;
  padding: 8px 10px; margin-bottom: 10px; font-size: 13px;
}
.vote-raw { display: block; margin-top: 4px; font-size: 11px; color: var(--sub); word-break: break-all; }
.vote-pick { font-size: 12.5px; color: var(--blue); margin-bottom: 4px; font-weight: 600; }

.engine-block.is-backbone { border: 1px solid var(--blue); }
.engine-block.is-winner { border-color: var(--green); }
.engine-block.is-excluded { opacity: 0.62; }
.engine-meta { font-size: 11px; color: var(--sub); margin-bottom: 4px; }
.etag { font-size: 10px; font-weight: 700; padding: 1px 6px; border-radius: 999px; margin-left: 4px; vertical-align: middle; }
.etag-bb { background: var(--blue-bg); color: var(--blue); }
.etag-ex { background: var(--sub-bg); color: var(--sub); }
.etag-win { background: var(--green-bg); color: var(--green); }

.spans { display: flex; flex-direction: column; gap: 8px; }
.span-card { background: var(--card); border: 1px solid var(--border); border-radius: 8px; padding: 8px 10px; }
.span-override { border-left: 3px solid var(--green); }
.span-tie { border-left: 3px solid var(--amber); }
.span-keep { border-left: 3px solid var(--blue); }
.span-ok { border-left: 3px solid var(--sub); }
.span-head { font-size: 12.5px; font-weight: 600; margin-bottom: 2px; }
.span-method { color: var(--purple); }
.span-hint { font-size: 11.5px; color: var(--sub); margin-bottom: 6px; }
.span-voted { border-color: var(--blue); margin-bottom: 6px; }
.span-dis { margin: 0; padding-left: 18px; font-size: 12px; }
.span-dis pre { margin-top: 4px; font-size: 11.5px; }
.span-pos { font-size: 12px; color: var(--amber); margin-top: 6px; }

/* vote từng chữ — tô màu theo phép biến đổi Levenshtein thật */
.han-diff { font-size: 14px; line-height: 1.8; }
.ch-eq { color: var(--text); }
.ch-rep { background: var(--red-bg); color: var(--red); border-radius: 3px; padding: 0 1px; }
.ch-ins { background: var(--amber-bg); color: var(--amber); border-radius: 3px; padding: 0 1px; }
.ch-gap { color: var(--sub); opacity: 0.5; letter-spacing: 1px; }
.ch-contested { text-decoration: underline; text-decoration-color: var(--red); text-decoration-thickness: 2px; text-underline-offset: 3px; }

.positions { margin-top: 8px; display: flex; flex-direction: column; gap: 4px; }
.pos-row { font-size: 11.5px; background: var(--card2); border: 1px solid var(--border); border-radius: 6px; padding: 5px 9px; }
.pos-fixed { border-left: 3px solid var(--green); }
.pos-open { border-left: 3px solid var(--amber); }
.pos-votes { color: var(--sub); font-size: 11px; margin-top: 3px; }

.doc-body { padding: 14px 4px 4px 20px; border-left: 2px solid var(--border); margin-top: 10px; }
.meta-table { border-collapse: collapse; font-size: 12.5px; margin-bottom: 10px; }
.meta-table td { padding: 3px 10px 3px 0; vertical-align: top; }
.meta-table td:first-child { color: var(--sub); white-space: nowrap; }
.engines-used { font-size: 12px; color: var(--sub); margin-bottom: 12px; }

details.page-detail {
  background: var(--card2); border: 1px solid var(--border); border-radius: 8px;
  margin-bottom: 6px; padding: 6px 10px;
}
details.page-detail > summary { cursor: pointer; font-size: 12.5px; list-style: none; }
details.page-detail > summary::-webkit-details-marker { display: none; }
details.page-detail > summary::before { content: "▸ "; color: var(--sub); }
details.page-detail[open] > summary::before { content: "▾ "; }

.page-body { padding: 10px 4px 2px 14px; }
.field-label { font-size: 11px; font-weight: 700; color: var(--sub); text-transform: uppercase; margin: 10px 0 4px; }
.field-label:first-child { margin-top: 0; }
pre { background: var(--card); border: 1px solid var(--border); border-radius: 6px; padding: 8px 10px;
      font-size: 12.5px; white-space: pre-wrap; word-break: break-word; margin: 0; font-family: "SF Mono", Menlo, monospace; }
pre.voted { border-color: var(--blue); }
.empty { color: var(--sub); font-size: 12px; font-style: italic; }

.engines-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(260px, 1fr)); gap: 8px; }
.engine-block .engine-name { font-size: 11px; font-weight: 700; color: var(--purple); margin-bottom: 3px; }

.pairs-list { display: flex; flex-direction: column; gap: 6px; }
.pair-row { display: grid; grid-template-columns: 1fr 24px 1.2fr; gap: 8px; align-items: center; }
.pair-han, .pair-viet {
  background: var(--card); border: 1px solid var(--border); border-radius: 7px;
  padding: 7px 10px; font-size: 12.5px; line-height: 1.5;
}
.pair-han { border-left: 3px solid var(--blue); }
.pair-viet { border-left: 3px solid var(--green); position: relative; }
.pair-arrow { text-align: center; color: var(--green); font-size: 14px; }
.pair-conf {
  display: inline-block; margin-left: 8px; font-size: 10px; font-weight: 700;
  padding: 1px 7px; border-radius: 999px; vertical-align: middle;
}
.conf-cao { background: var(--green-bg); color: var(--green); }
.conf-trung_binh { background: var(--amber-bg); color: var(--amber); }
.conf-thap { background: var(--red-bg); color: var(--red); }

.json-btn {
  font-size: 11px; font-weight: 700; padding: 2px 9px; border-radius: 999px;
  background: var(--card2); border: 1px solid var(--border); color: var(--sub);
  cursor: pointer; font-family: "SF Mono", Menlo, monospace;
}
.json-btn:hover { color: var(--text); border-color: var(--sub); }

.json-panel {
  position: fixed; top: 0; right: -640px; width: 620px; height: 100vh;
  background: var(--card); border-left: 1px solid var(--border);
  box-shadow: -8px 0 24px rgba(0,0,0,0.3);
  transition: right 0.2s ease; z-index: 100;
  display: flex; flex-direction: column;
}
.json-panel.open { right: 0; }
.json-panel-header {
  display: flex; align-items: center; justify-content: space-between;
  padding: 14px 16px; border-bottom: 1px solid var(--border);
  font-family: "SF Mono", Menlo, monospace; font-weight: 700; font-size: 13px;
}
.json-panel-close {
  background: var(--card2); border: 1px solid var(--border); color: var(--text);
  border-radius: 6px; padding: 4px 10px; cursor: pointer; font-size: 12px;
}
#json-panel-content {
  margin: 0; padding: 14px 16px; overflow: auto; flex-grow: 1;
  font-size: 11.5px; line-height: 1.5; white-space: pre-wrap; word-break: break-word;
}
.json-panel-overlay {
  position: fixed; inset: 0; background: rgba(0,0,0,0.35);
  z-index: 99; display: none;
}
.json-panel-overlay.open { display: block; }
"""

JS = """
function openJsonPanel(docId) {
  document.getElementById('json-panel-title').textContent = docId + '.json';
  document.getElementById('json-panel-content').textContent = 'Đang tải…';
  document.getElementById('json-panel').classList.add('open');
  document.getElementById('json-panel-overlay').classList.add('open');
  fetch('data/' + docId + '.json')
    .then(function(r) { return r.text(); })
    .then(function(txt) { document.getElementById('json-panel-content').textContent = txt; })
    .catch(function() { document.getElementById('json-panel-content').textContent = 'Lỗi tải data/' + docId + '.json'; });
}
function closeJsonPanel() {
  document.getElementById('json-panel').classList.remove('open');
  document.getElementById('json-panel-overlay').classList.remove('open');
}
document.addEventListener('keydown', function(e) {
  if (e.key === 'Escape') closeJsonPanel();
});

// Lazy-load thân từng tài liệu — XÁC NHẬN 2026-09-21: đây là phần cốt lõi
// sửa lag. Trước đó nội dung TẤT CẢ tài liệu (mọi trang, mọi engine) được
// nhúng sẵn trong chính file index.html (111MB) dù người xem chỉ mở 1 tài
// liệu. Giờ index.html chỉ chứa dòng tóm tắt; bấm mở (<details> toggle) mới
// fetch() đúng 1 file data/<doc_id>.html của tài liệu đó.
function loadDocBody(doc) {
  var el = document.getElementById('body-' + doc);
  if (!el || el.dataset.loaded) return;
  fetch('data/' + doc + '.html')
    .then(function(r) {
      if (!r.ok) throw new Error(r.status);
      return r.text();
    })
    .then(function(htm) {
      el.innerHTML = htm;
      el.dataset.loaded = '1';
    })
    .catch(function() {
      el.innerHTML = '<div class="empty">Lỗi tải data/' + doc + '.html — cần mở trang qua server tĩnh (vd. python3 -m http.server), không mở trực tiếp bằng file://.</div>';
    });
}
document.querySelectorAll('details.doc-detail').forEach(function(d) {
  d.addEventListener('toggle', function() {
    if (d.open) loadDocBody(d.dataset.docId);
  });
});
"""


def main() -> int:
    # XÁC NHẬN 2026-09-21: tách kiến trúc để hết lag — trước đó 1 file
    # index.html duy nhất (111MB) nhúng sẵn HTML+JSON của TOÀN BỘ 25 tài liệu
    # / 1256 trang, trình duyệt phải tải+parse hết dù chỉ xem 1 tài liệu. Giờ:
    #   dashboard/index.html        — khung nhẹ, chỉ có dòng tóm tắt 25 tài liệu
    #   dashboard/status.json       — số liệu tổng hợp (không có nội dung trang)
    #   dashboard/data/<doc_id>.html — nội dung đầy đủ 1 tài liệu, tải khi mở
    #   dashboard/data/<doc_id>.json — JSON gốc 1 tài liệu, tải khi bấm "JSON"
    raw_docs = load_records()
    data = build_data(raw_docs)
    raw_by_id = {d["doc_id"]: d for d in raw_docs}

    out_dir = ROOT / "dashboard"
    out_dir.mkdir(exist_ok=True)
    data_dir = out_dir / "data"
    data_dir.mkdir(exist_ok=True)

    for e in data["documents"]:
        doc_id = e["doc_id"]
        (data_dir / f"{doc_id}.html").write_text(render_doc_body(e), encoding="utf-8")
        raw = raw_by_id.get(doc_id)
        if raw is not None:
            (data_dir / f"{doc_id}.json").write_text(
                json.dumps(raw, ensure_ascii=False, indent=2), encoding="utf-8"
            )

    # status.json: bỏ "pages" (nội dung đầy đủ, đã có riêng ở data/<doc_id>.html/json)
    # — chỉ giữ số liệu tổng hợp (stats) để trang tổng quan hiện badge/pill.
    lean_docs = [{k: v for k, v in e.items() if k != "pages"} for e in data["documents"]]
    lean_data = {**data, "documents": lean_docs}

    json_path = out_dir / "status.json"
    json_path.write_text(json.dumps(lean_data, ensure_ascii=False, indent=2), encoding="utf-8")

    html_path = out_dir / "index.html"
    html_path.write_text(render_html(lean_data), encoding="utf-8")

    o = data["overall_stats"]
    print(f"Đã ghi {json_path}")
    print(f"Đã ghi {html_path}")
    print(f"Đã ghi {len(data['documents'])} file data/<doc_id>.html + .json trong {data_dir}")
    print(f"Tổng {o['total_docs']} tài liệu | nhóm: {o['by_group']} | "
          f"mã định danh: {o['with_ma_dinh_danh']} | L1 đủ: {o['l1_done_docs']} | "
          f"L2 đủ: {o['l2_done_docs']} | L3 đủ: {o['l3_done_docs']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
