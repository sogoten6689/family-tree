from __future__ import annotations

from typing import Any

from rapidfuzz.distance import Levenshtein

from app.hannom.engines import EngineResult

# Port (không import) từ
# research/hannom-bilingual-dataset/scripts/vote_ocr.py (VOTE_OCR_RULE.md —
# xem tài liệu đó để biết lịch sử/lý do từng bước). Giữ nguyên thuật toán,
# chỉ bỏ phần đọc file/catalog (vote_page, load_catalog, ADAPTERS, CLI) vì
# pipeline live nhận bytes ảnh trực tiếp, không đọc kết quả OCR đã cache sẵn
# trên đĩa theo book_id/stem.
#
# Thuật toán tổng quát cho N engine bất kỳ (không hardcode 5) — với đúng 2
# engine, luật "ép số lẻ" (xem rank_by_similarity) sẽ loại 1 engine khỏi vòng
# vote để tránh hoà 1-1, nên "vote" ban đầu (khi mới có 2 engine) chỉ chọn
# nguyên văn của engine có độ tương đồng trung bình cao hơn — vote theo từng
# dòng (line-level) chỉ thực sự kích hoạt từ 3 engine trở lên. Đây là hành vi
# đúng thiết kế, không phải bug.

SIM_MATCH = 0.92
SIM_NOTE_MIN = 0.30


def best_match(line: str, candidates: list[str]) -> tuple[str | None, float]:
    """Tìm dòng khớp nhất bằng Levenshtein normalized_similarity (0..1)."""
    best_text, best_sim = None, 0.0
    for c in candidates:
        sim = Levenshtein.normalized_similarity(line, c)
        if sim > best_sim:
            best_text, best_sim = c, sim
    return best_text, best_sim


def _bag_of_lines_similarity(lines_a: list[str], lines_b: list[str]) -> float:
    """Độ giống giữa 2 TẬP dòng, KHÔNG phụ thuộc thứ tự — trung bình 2 chiều
    của best_match() từng dòng bên này so với TOÀN BỘ dòng bên kia (tránh lỗi
    so 2 chuỗi nối liền theo thứ tự khi 1 engine đọc đúng nội dung nhưng khác
    thứ tự cột)."""

    def avg_best(src: list[str], dst: list[str]) -> float:
        sims = [best_match(line, dst)[1] for line in src if line]
        return sum(sims) / len(sims) if sims else 0.0

    if not lines_a or not lines_b:
        return 0.0
    return (avg_best(lines_a, lines_b) + avg_best(lines_b, lines_a)) / 2


def rank_by_similarity(
    results: dict[str, EngineResult], priority: list[str]
) -> tuple[list[str], dict[str, float]]:
    """Xếp hạng engine theo độ giống nhau trung bình với các engine khác
    (bag-of-lines, không giả định trước engine nào tốt hơn) — engine giống
    "đa số" nhất làm backbone. `priority` chỉ dùng để tie-break khi 2 engine
    có độ giống trung bình bằng hệt nhau (luôn đúng với N=2)."""
    names = list(results)
    lines = {n: results[n].lines for n in names}
    pair_sim: dict[tuple[str, str], float] = {}
    avg_sim: dict[str, float] = {}
    for n in names:
        others = [m for m in names if m != n]
        if not others:
            avg_sim[n] = 1.0
            continue
        total = 0.0
        for m in others:
            key = tuple(sorted((n, m)))
            if key not in pair_sim:
                pair_sim[key] = _bag_of_lines_similarity(lines[n], lines[m])
            total += pair_sim[key]
        avg_sim[n] = total / len(others)
    ranked = sorted(names, key=lambda n: (-avg_sim[n], priority.index(n) if n in priority else len(priority)))
    return ranked, avg_sim


def vote_line(backbone_name: str, backbone_line: str, other_lines: dict[str, str]) -> dict[str, Any]:
    """Vote cả dòng giữa backbone_line và dòng khớp nhất từ mỗi engine khác.
    Gom dòng "cùng câu" (kể cả lệch độ dài) vào 1 cụm bằng Levenshtein MED
    thật, cụm nào nhiều engine đồng ý hơn cụm chứa backbone thì thắng."""
    candidates: list[tuple[str, str]] = [(backbone_name, backbone_line), *other_lines.items()]
    clusters: list[list[tuple[str, str]]] = []
    for name, text in candidates:
        for cluster in clusters:
            if Levenshtein.normalized_similarity(text, cluster[0][1]) >= SIM_MATCH:
                cluster.append((name, text))
                break
        else:
            clusters.append([(name, text)])

    backbone_cluster = next(c for c in clusters if any(n == backbone_name for n, _ in c))
    best_cluster = max(clusters, key=len)

    if len(best_cluster) > len(backbone_cluster):
        winner_cluster, method = best_cluster, "line_majority_override"
    elif len(clusters) == 1:
        winner_cluster, method = backbone_cluster, "line_unanimous"
    elif len(backbone_cluster) > 1:
        winner_cluster, method = backbone_cluster, "line_confirmed_majority"
    else:
        winner_cluster, method = backbone_cluster, "line_no_majority"

    if len(winner_cluster) == 1:
        voted_line = winner_cluster[0][1]
    else:
        voted_line = min(
            (text for _, text in winner_cluster),
            key=lambda t: sum(Levenshtein.distance(t, other) for _, other in winner_cluster),
        )

    winner_names = {n for n, _ in winner_cluster}
    disagreeing = [
        {
            "engine": name,
            "text": text,
            "similarity": round(Levenshtein.normalized_similarity(text, voted_line), 4),
        }
        for name, text in candidates
        if name not in winner_names
    ]

    return {
        "voted_line": voted_line,
        "method": method,
        "n_agree": len(winner_cluster),
        "n_total": len(candidates),
        "disagreeing": disagreeing,
    }


def vote_line_positional(
    backbone_name: str, backbone_line: str, other_lines: dict[str, str], min_majority: int = 3
) -> dict[str, Any]:
    """Fallback khi vote_line() không cho kết quả rõ ràng — căn từng engine
    khác vào đúng vị trí ký tự của backbone (Levenshtein.editops, star
    alignment), vote riêng từng vị trí/khe hở, chỉ tự sửa khi >= min_majority
    engine đồng thuận tại đúng 1 vị trí."""
    n = len(backbone_line)
    position_votes: dict[int, dict[str, list[str]]] = {i: {"__keep__": [backbone_name]} for i in range(n)}
    insert_run_by_gap: dict[int, dict[str, str]] = {i: {} for i in range(n + 1)}

    for name, line in other_lines.items():
        ops = Levenshtein.editops(backbone_line, line)
        touched_positions: set[int] = set()
        for op in sorted(ops, key=lambda o: (o.src_pos, o.dest_pos)):
            if op.tag == "replace":
                touched_positions.add(op.src_pos)
                position_votes[op.src_pos].setdefault(line[op.dest_pos], []).append(name)
            elif op.tag == "delete":
                touched_positions.add(op.src_pos)
                position_votes[op.src_pos].setdefault("__delete__", []).append(name)
            elif op.tag == "insert":
                gap = insert_run_by_gap[op.src_pos]
                gap[name] = gap.get(name, "") + line[op.dest_pos]
        for i in range(n):
            if i not in touched_positions:
                position_votes[i]["__keep__"].append(name)

    result_parts: list[str] = []
    uncertain_positions: list[dict[str, Any]] = []

    for i in range(n + 1):
        runs_by_engine = insert_run_by_gap[i]
        max_len = max((len(r) for r in runs_by_engine.values()), default=0)
        for j in range(max_len):
            sub_votes: dict[str, list[str]] = {"": [backbone_name]}
            for name, run in runs_by_engine.items():
                val = run[j] if j < len(run) else ""
                sub_votes.setdefault(val, []).append(name)
            for name in other_lines:
                if name not in runs_by_engine:
                    sub_votes[""].append(name)
            best_value, best_voters = max(sub_votes.items(), key=lambda kv: len(kv[1]))
            if best_value != "" and len(best_voters) >= min_majority:
                result_parts.append(best_value)
                uncertain_positions.append(
                    {
                        "gap_before": i,
                        "insert_index": j,
                        "resolved": best_value,
                        "method": "gap_majority_override",
                        "votes": sub_votes,
                    }
                )
            elif len(sub_votes) > 1:
                uncertain_positions.append(
                    {
                        "gap_before": i,
                        "insert_index": j,
                        "resolved": None,
                        "method": "gap_no_majority",
                        "votes": sub_votes,
                    }
                )

        if i == n:
            break
        pvotes = position_votes[i]
        pbest_value, pbest_voters = max(pvotes.items(), key=lambda kv: len(kv[1]))
        if pbest_value != "__keep__" and len(pbest_voters) >= min_majority:
            if pbest_value != "__delete__":
                result_parts.append(pbest_value)
            uncertain_positions.append(
                {
                    "backbone_pos": i,
                    "backbone_char": backbone_line[i],
                    "resolved": None if pbest_value == "__delete__" else pbest_value,
                    "method": "position_majority_override",
                    "votes": pvotes,
                }
            )
        else:
            result_parts.append(backbone_line[i])
            if len(pvotes) > 1:
                uncertain_positions.append(
                    {
                        "backbone_pos": i,
                        "backbone_char": backbone_line[i],
                        "resolved": None,
                        "method": "position_no_majority",
                        "votes": pvotes,
                    }
                )

    return {
        "voted_line": "".join(result_parts),
        "n_total": 1 + len(other_lines),
        "uncertain_positions": uncertain_positions,
    }


def vote_from_results(results: dict[str, EngineResult], priority: list[str]) -> dict[str, Any]:
    """Vote toàn bộ các dòng của 1 ảnh từ dict engine -> EngineResult.
    `priority` = danh sách engine đã cấu hình (settings HANNOM_VOTE_ENGINES),
    chỉ dùng tie-break khi 2 engine có độ giống trung bình bằng hệt nhau."""
    if not results:
        return {
            "voted_text": None,
            "vote_method": None,
            "engines": {},
            "uncertain_spans": [],
            "structural_diffs": [],
            "uncertain_rate": 0.0,
        }

    ranked, avg_sim = rank_by_similarity(results, priority)
    backbone_name = ranked[0]
    backbone = results[backbone_name]

    engines_out: dict[str, Any] = {}
    for name, r in results.items():
        avg_score = (sum(r.scores.values()) / len(r.scores)) if r.scores else None
        engines_out[name] = {
            "text": "\n".join(r.lines),
            "score": avg_score,
            "similarity_to_others": round(avg_sim[name], 4),
        }

    other_names = ranked[1:]

    excluded_from_vote = None
    if len(other_names) % 2 == 1:
        excluded_from_vote = other_names[-1]
        other_names = other_names[:-1]

    voted_lines: list[str] = []
    uncertain_spans: list[dict[str, Any]] = []

    for i, line in enumerate(backbone.lines):
        other_best: dict[str, str] = {}
        for name in other_names:
            match_text, sim = best_match(line, results[name].lines)
            if match_text is not None and sim >= SIM_NOTE_MIN:
                other_best[name] = match_text
        resolved = vote_line(backbone_name, line, other_best)
        voted_line = resolved["voted_line"]

        positional = None
        if resolved["method"] in ("line_no_majority", "line_confirmed_majority") and other_best:
            positional = vote_line_positional(backbone_name, line, other_best)
            voted_line = positional["voted_line"]

        voted_lines.append(voted_line)
        if resolved["method"] != "line_unanimous" or resolved["disagreeing"] or positional is not None:
            span: dict[str, Any] = {"line": i, **resolved}
            if positional is not None:
                span["voted_line"] = voted_line
                span["positional"] = positional
            uncertain_spans.append(span)

    n_lines = len(backbone.lines) or 1
    excl_note = f"_excl_{excluded_from_vote}_for_odd" if excluded_from_vote else ""
    if other_names:
        method = f"{backbone_name}_backbone_line_vote_levenshtein_{len(other_names)}_other{excl_note}"
    else:
        method = f"{backbone_name}_only_no_other_engine{excl_note}"

    return {
        "voted_text": "\n".join(voted_lines),
        "vote_method": method,
        "engines": engines_out,
        "uncertain_spans": uncertain_spans,
        "structural_diffs": [],
        "uncertain_rate": round(len(uncertain_spans) / n_lines, 4),
    }
