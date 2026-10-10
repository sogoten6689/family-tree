"""Xuất ``gold.training.json`` → CoNLL IOB2 cho NER (Hán: mức ký tự; Việt: mức từ/âm tiết).

Nguồn gốc duy nhất của nhãn là ``gold.training.json`` (xem docs/schemas/NER_RE_LABEL_SCHEMA_AND_PIPELINE.md);
file này SINH ra CoNLL, không bao giờ sửa tay CoNLL.

Điểm quan trọng — kiểm tra và sửa offset:
- Mỗi entity phải thoả ``text[start:end] == entity["text"]``.
- Python đếm theo code point, còn trình duyệt (Label Studio) có thể đếm theo đơn vị UTF-16. Hai cách
  KHÁC nhau với ký tự ngoài mặt phẳng cơ bản (nhiều chữ Nôm/Hán mở rộng, ví dụ ``𠊚``). Vì chưa rõ
  chính xác hành vi của bản Label Studio đang dùng, module này không tin offset mù quáng: thử theo code
  point trước; nếu lệch thì thử diễn giải như UTF-16 và đổi sang code point; nếu vẫn lệch thì BỎ entity và
  đếm lại trong ``stats``. Mọi trường hợp đều được thống kê để nhìn thấy mức độ lệch thật.

Chạy (từ thư mục ``research/``)::

    # Việt: cùng cách chia tập theo cây với bộ SFT (cùng seed thì cùng cây vào cùng tập)
    python -m label_studio_pipeline.export_conll vi --gold-dir <v2> --human-dir <v1_human> --output <dir>

    # Bất kỳ: danh sách file gold.training.json → 1 file CoNLL
    python -m label_studio_pipeline.export_conll files --unit char --output han.conll a.json b.json
"""

from __future__ import annotations

import argparse
import json
import logging
import re
import sys
from bisect import bisect_left, bisect_right
from collections import Counter
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable, Optional

logger = logging.getLogger(__name__)

HAN_SENTENCE_END = frozenset("。！？；")
VI_SENTENCE_END = frozenset(".!?;")
# Âm tiết/từ Việt (kể cả dấu tổ hợp rời khi văn bản ở dạng NFD) hoặc một ký tự dấu câu.
_WORD_TOKEN = re.compile(r"(?:\w|[̀-ͯ])+|[^\w\s]", re.UNICODE)

DEFAULT_MAX_TOKENS = 128


@dataclass(frozen=True)
class Span:
    start: int  # code point, bao gồm
    end: int  # code point, không bao gồm
    label: str


@dataclass(frozen=True)
class Token:
    text: str
    start: int
    end: int


# --------------------------------------------------------------------------- offset


def _utf16_boundaries(text: str) -> dict[int, int]:
    """Ánh xạ vị trí UTF-16 → chỉ số code point, chỉ tại ranh giới ký tự (không nằm giữa cặp thay thế)."""
    mapping: dict[int, int] = {}
    unit = 0
    for index, char in enumerate(text):
        mapping[unit] = index
        unit += 2 if ord(char) > 0xFFFF else 1
    mapping[unit] = len(text)
    return mapping


def resolve_offsets(text: str, entities: Iterable[dict], counters: Counter) -> list[Span]:
    """Đổi entity trong gold thành Span theo code point, loại entity lệch/chồng và thống kê lý do."""
    boundaries: Optional[dict[int, int]] = None
    ok: list[Span] = []
    for entity in entities:
        counters["entities_in"] += 1
        label, expected = entity.get("label"), entity.get("text")
        start, end = entity.get("start"), entity.get("end")
        if not isinstance(label, str) or not isinstance(expected, str) or not isinstance(start, int) or not isinstance(end, int):
            counters["entity_malformed"] += 1
            continue
        if 0 <= start < end <= len(text) and text[start:end] == expected:
            ok.append(Span(start, end, label))
            counters["offset_ok"] += 1
            continue
        if boundaries is None:
            boundaries = _utf16_boundaries(text)
        s, e = boundaries.get(start), boundaries.get(end)
        if s is not None and e is not None and s < e and text[s:e] == expected:
            ok.append(Span(s, e, label))
            counters["offset_utf16_converted"] += 1
            continue
        counters["offset_mismatch_dropped"] += 1
        logger.debug("offset lệch: [%s,%s) %r != %r", start, end, text[start:end] if 0 <= start <= end <= len(text) else None, expected)

    ok.sort(key=lambda span: (span.start, -(span.end - span.start)))
    result: list[Span] = []
    last_end = -1
    for span in ok:
        if span.start < last_end:
            counters["overlap_dropped"] += 1
            continue
        result.append(span)
        last_end = span.end
    return result


# --------------------------------------------------------------------------- tokenize


def tokenize(text: str, unit: str) -> list[Token]:
    """``char``: mỗi ký tự không phải khoảng trắng là một token (Hán). ``word``: âm tiết/từ + dấu câu (Việt)."""
    if unit == "char":
        return [Token(ch, i, i + 1) for i, ch in enumerate(text) if not ch.isspace()]
    if unit == "word":
        return [Token(m.group(), m.start(), m.end()) for m in _WORD_TOKEN.finditer(text)]
    raise ValueError(f"unit không hợp lệ: {unit!r} (char|word)")


def _line_ids(text: str, tokens: list[Token]) -> list[int]:
    """Số thứ tự dòng của từng token (đếm ký tự xuống dòng đứng trước token)."""
    ids, line, prev = [], 0, 0
    for token in tokens:
        line += text.count("\n", prev, token.start)
        prev = token.start
        ids.append(line)
    return ids


# --------------------------------------------------------------------------- align + tag


def align_spans(tokens: list[Token], spans: list[Span], misaligned: str, counters: Counter) -> list[tuple[int, int, str]]:
    """Span (code point) → (token đầu, token cuối+1, nhãn). Ranh giới nằm giữa token: ``snap`` mở rộng ra đủ
    token, ``drop`` bỏ entity. Span không phủ token nào (toàn khoảng trắng) bị bỏ."""
    aligned: list[tuple[int, int, str]] = []
    last_stop = 0  # sau khi mở rộng (snap), hai entity có thể rơi vào cùng một token → bỏ entity sau
    starts = [tok.start for tok in tokens]
    ends = [tok.end for tok in tokens]
    for span in spans:
        # token đầu = token đầu tiên có end > span.start; token cuối = token cuối cùng có start < span.end
        first = bisect_right(ends, span.start)
        last = bisect_left(starts, span.end) - 1
        if first >= len(tokens) or last < first:
            counters["entity_no_token_dropped"] += 1
            continue
        exact = tokens[first].start == span.start and tokens[last].end == span.end
        if not exact:
            if misaligned == "drop":
                counters["misaligned_dropped"] += 1
                continue
            counters["misaligned_snapped"] += 1
        if first < last_stop:
            counters["overlap_after_snap_dropped"] += 1
            continue
        aligned.append((first, last + 1, span.label))
        last_stop = last + 1
    return aligned


def bio_tags(n_tokens: int, aligned: list[tuple[int, int, str]]) -> list[str]:
    tags = ["O"] * n_tokens
    for first, stop, label in aligned:
        tags[first] = f"B-{label}"
        for i in range(first + 1, stop):
            tags[i] = f"I-{label}"
    return tags


def _sentence_ranges(
    tokens: list[Token], lines: list[int], aligned: list[tuple[int, int, str]], *, unit: str, line_breaks: str, max_tokens: int, counters: Counter
) -> list[tuple[int, int]]:
    """Chia dãy token thành câu: theo dấu kết câu, (tuỳ chọn) theo xuống dòng, và cắt cứng ở ``max_tokens``
    nhưng KHÔNG cắt giữa một entity."""
    enders = HAN_SENTENCE_END if unit == "char" else VI_SENTENCE_END
    inside = [False] * (len(tokens) + 1)  # inside[i]: ranh giới trước token i nằm TRONG một entity
    for first, stop, _ in aligned:
        for i in range(first + 1, stop):
            inside[i] = True

    ranges: list[tuple[int, int]] = []
    start = 0
    for i in range(len(tokens)):
        last = i == len(tokens) - 1
        boundary = last or (line_breaks == "split" and lines[i + 1] != lines[i]) or tokens[i].text in enders
        if boundary and (last or not inside[i + 1]):
            ranges.append((start, i + 1))
            start = i + 1
    result: list[tuple[int, int]] = []
    for a, b in ranges:
        while b - a > max_tokens:
            cut = a + max_tokens
            while cut > a + 1 and inside[cut]:
                cut -= 1
            if inside[cut]:  # entity dài hơn max_tokens: chấp nhận câu dài hơn
                cut = a + max_tokens
                while cut < b and inside[cut]:
                    cut += 1
                counters["entity_longer_than_max_tokens"] += 1
            result.append((a, cut))
            a = cut
        if a < b:
            result.append((a, b))
    return result


def convert_document(
    doc: dict,
    *,
    unit: str,
    line_breaks: str = "auto",
    misaligned: str = "snap",
    max_tokens: int = DEFAULT_MAX_TOKENS,
    counters: Optional[Counter] = None,
) -> list[list[tuple[str, str]]]:
    """Một gold.training.json → danh sách câu; mỗi câu là danh sách (token, tag).

    ``line_breaks``: ``split`` (xuống dòng = hết câu; hợp văn xuôi quốc ngữ), ``ignore`` (xuống dòng là
    ngắt cột của OCR — một tên có thể nằm vắt qua hai dòng; hợp văn bản Hán), ``auto`` = ``ignore`` cho
    ``char``, ``split`` cho ``word``.
    """
    counters = counters if counters is not None else Counter()
    if line_breaks == "auto":
        line_breaks = "ignore" if unit == "char" else "split"
    text = doc["text"]
    spans = resolve_offsets(text, doc.get("entities") or [], counters)
    tokens = tokenize(text, unit)
    if not tokens:
        return []
    aligned = align_spans(tokens, spans, misaligned, counters)
    tags = bio_tags(len(tokens), aligned)
    counters["entities_out"] += len(aligned)
    counters["tokens"] += len(tokens)
    sentences = _sentence_ranges(
        tokens, _line_ids(text, tokens), aligned, unit=unit, line_breaks=line_breaks, max_tokens=max_tokens, counters=counters
    )
    counters["sentences"] += len(sentences)
    return [[(tokens[i].text, tags[i]) for i in range(a, b)] for a, b in sentences]


def write_conll(path: Path, sentences: Iterable[list[tuple[str, str]]], sep: str = "\t") -> int:
    path.parent.mkdir(parents=True, exist_ok=True)
    n = 0
    with path.open("w", encoding="utf-8") as fh:
        for sentence in sentences:
            for token, tag in sentence:
                fh.write(f"{token}{sep}{tag}\n")
            fh.write("\n")
            n += 1
    return n


# --------------------------------------------------------------------------- dataset


def _load(path: Path) -> Optional[dict]:
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def export_vi_dataset(
    *,
    gold_dir: Path,
    human_dir: Path,
    stratified_path: Path,
    output_dir: Path,
    val_ratio: float,
    seed: int,
    prefer_human: bool,
    max_tokens: int,
    misaligned: str,
    sep: str,
) -> dict:
    """Bộ CoNLL tiếng Việt, mức từ, chia tập THEO CÂY giống hệt bộ SFT (dùng chung ``plan_splits``)."""
    from label_studio_pipeline.build_llm_sft_dataset import plan_splits

    plan = plan_splits(
        gold_dir=gold_dir,
        human_dir=human_dir,
        stratified_path=stratified_path,
        val_ratio=val_ratio,
        seed=seed,
        prefer_human=prefer_human,
    )
    stats: dict[str, dict] = {}
    for split, items in plan.items():
        counters: Counter = Counter()
        sentences: list[list[tuple[str, str]]] = []
        for tree_id, source in items:
            base = human_dir if source == "human" else gold_dir
            doc = _load(base / str(tree_id) / "gold.training.json")
            if doc is None:
                counters["missing_docs"] += 1
                logger.warning("thiếu %s doc của cây %s", source, tree_id)
                continue
            lang = doc.get("lang", "vi")
            if lang != "vi":
                counters["skipped_non_vi"] += 1
                continue
            counters["docs"] += 1
            counters[f"docs_{source}"] += 1
            sentences.extend(
                convert_document(doc, unit="word", misaligned=misaligned, max_tokens=max_tokens, counters=counters)
            )
        write_conll(output_dir / f"{split}.conll", sentences, sep=sep)
        stats[split] = {"tree_ids": [t for t, _ in items], **dict(counters)}
    summary = {
        "version": 1,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "params": {
            "unit": "word",
            "val_ratio": val_ratio,
            "seed": seed,
            "prefer_human": prefer_human,
            "max_tokens": max_tokens,
            "misaligned": misaligned,
            "separator": "tab" if sep == "\t" else "space",
        },
        "label_note": "silver = Gemini/rule, chưa người duyệt; human = Label Studio v1_human. Chỉ human dùng đánh giá cuối.",
        "splits": stats,
    }
    (output_dir / "stats.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    return summary


def export_files(
    paths: list[Path], *, output: Path, unit: str, line_breaks: str, misaligned: str, max_tokens: int, sep: str
) -> dict:
    counters: Counter = Counter()
    sentences: list[list[tuple[str, str]]] = []
    for path in paths:
        doc = json.loads(path.read_text(encoding="utf-8"))
        counters["docs"] += 1
        sentences.extend(
            convert_document(doc, unit=unit, line_breaks=line_breaks, misaligned=misaligned, max_tokens=max_tokens, counters=counters)
        )
    write_conll(output, sentences, sep=sep)
    summary = {"files": [str(p) for p in paths], "unit": unit, **dict(counters)}
    output.with_suffix(".stats.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    return summary


def main(argv: Optional[list[str]] = None) -> int:
    from label_studio_pipeline.data_layout import DATA_ROOT, GOLD_LABELS, GOLD_STRATIFIED

    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest="cmd", required=True)

    def common(p: argparse.ArgumentParser) -> None:
        p.add_argument("--max-tokens", type=int, default=DEFAULT_MAX_TOKENS)
        p.add_argument("--misaligned", choices=("snap", "drop"), default="snap",
                       help="entity có ranh giới nằm giữa token: snap = mở rộng ra đủ token, drop = bỏ entity")
        p.add_argument("--sep", choices=("tab", "space"), default="tab",
                       help="tab khớp parse_conll_file trong FINETUNE_DATA_PREPARATION.md (ví dụ ở đó lại dùng dấu cách)")
        p.add_argument("-v", "--verbose", action="store_true")

    vi = sub.add_parser("vi", help="bộ tiếng Việt chia tập theo cây (cùng cách chia với bộ SFT)")
    vi.add_argument("--gold-dir", type=Path, default=DATA_ROOT / "01_interim" / "gemini_review" / "v2")
    vi.add_argument("--human-dir", type=Path, default=GOLD_LABELS / "v1_human")
    vi.add_argument("--stratified", type=Path, default=GOLD_STRATIFIED)
    vi.add_argument("--output", type=Path, default=DATA_ROOT / "03_derived" / "conll" / "vi_v1")
    vi.add_argument("--val-ratio", type=float, default=0.1)
    vi.add_argument("--seed", type=int, default=42)
    vi.add_argument("--no-prefer-human", dest="prefer_human", action="store_false")
    common(vi)

    files = sub.add_parser("files", help="danh sách gold.training.json → 1 file CoNLL")
    files.add_argument("inputs", nargs="+", type=Path)
    files.add_argument("--output", type=Path, required=True)
    files.add_argument("--unit", choices=("char", "word"), required=True)
    files.add_argument("--line-breaks", choices=("auto", "split", "ignore"), default="auto")
    common(files)

    args = parser.parse_args(argv)
    logging.basicConfig(level=logging.DEBUG if args.verbose else logging.INFO, format="%(levelname)s %(message)s")
    sep = "\t" if args.sep == "tab" else " "
    if args.cmd == "vi":
        summary = export_vi_dataset(
            gold_dir=args.gold_dir, human_dir=args.human_dir, stratified_path=args.stratified, output_dir=args.output,
            val_ratio=args.val_ratio, seed=args.seed, prefer_human=args.prefer_human,
            max_tokens=args.max_tokens, misaligned=args.misaligned, sep=sep,
        )
        for split, st in summary["splits"].items():
            logger.info("%-12s docs=%s câu=%s token=%s entity=%s lệch=%s utf16=%s chồng=%s", split, st.get("docs", 0),
                        st.get("sentences", 0), st.get("tokens", 0), st.get("entities_out", 0),
                        st.get("offset_mismatch_dropped", 0), st.get("offset_utf16_converted", 0), st.get("overlap_dropped", 0))
    else:
        summary = export_files(
            args.inputs, output=args.output, unit=args.unit, line_breaks=args.line_breaks,
            misaligned=args.misaligned, max_tokens=args.max_tokens, sep=sep,
        )
        logger.info("%s", json.dumps({k: v for k, v in summary.items() if k != "files"}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
