from __future__ import annotations

from typing import Any

from rapidfuzz.distance import Levenshtein

# Diff từng chữ cho phần hiển thị vote (VoteDiffLine.tsx) — cùng cách tô màu
# với `char_diff_spans`/`voted_line_contested_html` trong
# hannom-bilingual-dataset/scripts/build_dashboard.py, nhưng trả về segment
# thay vì HTML. Tính ở Python (code point) thay vì JS (UTF-16) vì nhiều chữ
# Hán Nôm nằm ngoài BMP — làm ở JS sẽ lệch chỉ số (bài học "Sổ Khảo Dị OCR"
# 2026-09-15). Frontend chỉ việc nối segment, không tính chỉ số nào.


def char_diff_segments(voted: str, other: str) -> list[dict[str, Any]]:
    """`other` chia theo phép biến đổi Levenshtein so với `voted`:
    equal/replace/insert mang `text` của `other`; delete (chữ `other` thiếu
    so với `voted`) mang `missing` = số chữ thiếu."""
    segments: list[dict[str, Any]] = []
    for op in Levenshtein.opcodes(voted, other):
        if op.tag == "delete":
            segments.append({"op": "delete", "missing": op.src_end - op.src_start})
        else:
            segments.append({"op": op.tag, "text": other[op.dest_start:op.dest_end]})
    return segments


def voted_line_segments(voted: str, disagreeing: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Câu thắng chia thành đoạn liền nhau, `contested=True` ở mọi chữ có
    ≥1 engine đọc khác đi (replace/delete — giống dashboard, chữ chèn thêm
    không có vị trí trên câu thắng nên không gạch chân)."""
    if not voted:
        return []
    mask = [False] * len(voted)
    for d in disagreeing:
        for op in Levenshtein.opcodes(voted, d.get("text") or ""):
            if op.tag != "equal":
                for i in range(op.src_start, op.src_end):
                    mask[i] = True

    segments: list[dict[str, Any]] = []
    for ch, contested in zip(voted, mask):
        if segments and segments[-1]["contested"] == contested:
            segments[-1]["text"] += ch
        else:
            segments.append({"text": ch, "contested": contested})
    return segments


def annotate_vote_diffs(vote_meta: dict[str, Any] | None) -> dict[str, Any] | None:
    """Gắn `voted_segments` vào từng uncertain span và `diff` vào từng engine
    bất đồng. Không đổi field có sẵn; gọi lại nhiều lần cho cùng kết quả."""
    if not vote_meta:
        return vote_meta
    for span in vote_meta.get("uncertain_spans") or []:
        voted = span.get("voted_line") or ""
        disagreeing = span.get("disagreeing") or []
        span["voted_segments"] = voted_line_segments(voted, disagreeing)
        for d in disagreeing:
            d["diff"] = char_diff_segments(voted, d.get("text") or "")
    return vote_meta
