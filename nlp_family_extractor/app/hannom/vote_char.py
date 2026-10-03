"""Vote OCR theo TỪNG CHỮ trên cả trang (thuật toán "char_majority", 2026-10-04).

NGUỒN DUY NHẤT của thuật toán — research/hannom-bilingual-dataset/scripts/
vote_char_majority.py nạp thẳng file này (không qua package `app`, vì
app/hannom/__init__.py kéo theo pipeline/httpx). File chỉ được phụ thuộc
rapidfuzz + thư viện chuẩn.

Khác `vote_ocr.vote_from_results` (vote theo dòng, loại 1 engine cho số phiếu lẻ,
vote ký tự cần ≥3 engine trong số engine được bỏ phiếu):

1. Mỗi engine → 1 chuỗi chữ Hán của CẢ TRANG theo thứ tự đọc (bỏ dấu câu, khoảng
   trắng, Latin). Không ghép dòng → không có lỗi ghép nhầm dòng ngắn / tên người
   khác; chỗ ngắt dòng khác nhau giữa engine không còn ảnh hưởng.
2. Căn từng engine vào engine NỀN theo chữ (Levenshtein opcodes), mọi engine đều
   bỏ phiếu (không loại engine nào).
3. Mỗi vị trí chữ của nền: đếm phiếu (gồm cả phiếu "không có chữ").
   - Chữ khác nền, nhiều phiếu nhất (hơn hẳn) và ≥ AUTO_MIN (3)  → TỰ SỬA.
   - Như trên nhưng ≥ SUGGEST_MIN (2)                           → ĐỀ XUẤT (giữ nền).
   - Hoà                                                          → giữ nền, CẦN SOÁT.
   Chữ thừa / chữ thiếu (thêm, xoá) chỉ ĐỀ XUẤT, không bao giờ tự sửa: engine đọc
   lệch thứ tự 1 đoạn trông như "thiếu chữ", tự xoá sẽ mất chữ thật.
   Quy ước 3/4 tự sửa, 2/4 đề xuất: Lâm chốt 03/10/2026 — ngưỡng là ≥3 PHIẾU tuyệt đối
   (5 engine: 3/5 vẫn tự sửa; 3 engine: chỉ đề xuất).
4. Sàng engine trước khi bỏ phiếu (mỗi trang), ngưỡng đặt theo phân bố đo trên 19 bộ:
   - LẠC ĐỀ: < OUTLIER_COVERAGE chữ của engine có mặt ở engine nào khác, dài > 2× trung vị
     các engine kia và ≥ 20 chữ (vd DeepSeek đọc lặp 52.232 chữ, nom-557 tr.49).
   - LỆCH THỨ TỰ so với nền: cùng chữ (tập chữ ≥ ORDER_MIN_BAG) nhưng giống theo thứ tự
     thấp hơn ≥ ORDER_GAP → căn chữ vô nghĩa, không cho bỏ phiếu.
   Còn < 2 engine bỏ phiếu → cả trang "unaligned" (cần soát toàn trang).

Kết quả giữ ranh giới dòng của engine nền. Hàm thuần, không gọi API.
"""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, field
from typing import Any

from rapidfuzz.distance import Levenshtein

AUTO_MIN = 3
SUGGEST_MIN = 2
NO_CHAR = ""
OUTLIER_COVERAGE = 0.3
OUTLIER_MIN_CHARS = 20
ORDER_MIN_BAG = 0.3
ORDER_GAP = 0.3


def is_han(ch: str) -> bool:
    cp = ord(ch)
    return (
        0x3400 <= cp <= 0x4DBF
        or 0x4E00 <= cp <= 0x9FFF
        or 0xF900 <= cp <= 0xFAFF
        or 0x20000 <= cp <= 0x323AF
        or 0x2F800 <= cp <= 0x2FA1F
        or ch == "〇"
    )


def han_only(text: str) -> str:
    return "".join(ch for ch in text if is_han(ch))


def _common(a: str, b: str) -> int:
    return sum((Counter(a) & Counter(b)).values())


def find_outliers(texts: dict[str, str]) -> dict[str, str]:
    """Engine "lạc đề" (không phụ thuộc engine nền). `texts`: engine → chuỗi chữ Hán cả trang."""
    texts = {k: v for k, v in texts.items() if v}
    out: dict[str, str] = {}
    if len(texts) < 3:
        return out  # 2 engine: không biết bên nào lạc
    for name, text in texts.items():
        others = [t for k, t in texts.items() if k != name]
        coverage = max(_common(text, t) for t in others) / len(text)
        median_other = sorted(len(t) for t in others)[len(others) // 2]
        if coverage < OUTLIER_COVERAGE and len(text) >= OUTLIER_MIN_CHARS and len(text) > 2 * median_other:
            out[name] = f"lạc đề: {coverage:.0%} chữ có ở engine khác, {len(text)} chữ (trung vị khác {median_other})"
    return out


def find_order_mismatch(texts: dict[str, str], backbone: str) -> dict[str, str]:
    """Engine cùng chữ với nền nhưng lệch thứ tự đọc."""
    out: dict[str, str] = {}
    bb = texts.get(backbone) or ""
    for name, text in texts.items():
        if name == backbone or not text or not bb:
            continue
        bag = _common(text, bb) / max(len(text), len(bb))
        ordered = Levenshtein.normalized_similarity(text, bb)
        if bag >= ORDER_MIN_BAG and bag - ordered >= ORDER_GAP:
            out[name] = f"lệch thứ tự: giống theo tập chữ {bag:.0%}, theo thứ tự {ordered:.0%}"
    return out


@dataclass
class Slot:
    """1 vị trí chữ của nền (kind="char") hoặc 1 khe chèn trước vị trí đó (kind="insert")."""

    kind: str
    index: int
    backbone: str
    votes: dict[str, list[str]]  # giá trị → engine
    status: str  # unanimous | kept | kept_weak | auto_fixed | suggested | tie | unaligned
    final: str
    proposal: str | None = None
    line: int = 0


@dataclass
class PageVote:
    backbone: str
    engines: list[str]
    lines: list[str]  # văn bản kết quả, theo dòng của nền
    slots: list[Slot] = field(default_factory=list)
    excluded: dict[str, str] = field(default_factory=dict)  # engine → lý do không cho bỏ phiếu
    page_status: str = "ok"  # ok | partial (có engine bị loại) | unaligned (< 2 engine bỏ phiếu)

    def counts(self) -> Counter:
        return Counter(s.status for s in self.slots if s.kind == "char")

    def review_rate(self) -> float:
        """Tỉ lệ chữ cần người soát: đề xuất + hoà + giữ nền nhưng < AUTO_MIN phiếu."""
        chars = [s for s in self.slots if s.kind == "char"]
        need = sum(s.status in ("suggested", "tie", "kept_weak", "unaligned") for s in chars)
        return need / len(chars) if chars else 0.0


def _decide(backbone_value: str, votes: dict[str, list[str]], allow_auto: bool) -> tuple[str, str, str | None]:
    """→ (status, final, proposal)."""
    ranked = sorted(((len(e), v) for v, e in votes.items()), key=lambda x: (-x[0], x[1] != backbone_value))
    top_n, top = ranked[0]
    second_n = ranked[1][0] if len(ranked) > 1 else 0
    if len(votes) == 1:
        return "unanimous", backbone_value, None
    if top_n == second_n:
        return "tie", backbone_value, None
    if top == backbone_value:
        return ("kept" if top_n >= AUTO_MIN else "kept_weak"), backbone_value, None
    if allow_auto and top_n >= AUTO_MIN:
        return "auto_fixed", top, None
    if top_n >= SUGGEST_MIN:
        return "suggested", backbone_value, top
    return "tie", backbone_value, None


def vote_page_chars(engine_lines: dict[str, list[str]], backbone: str, screen: bool = True) -> PageVote:
    """`engine_lines`: engine → các dòng theo THỨ TỰ ĐỌC. `backbone`: engine nền
    (nên chọn SAU khi bỏ engine lạc đề — xem find_outliers)."""
    excluded: dict[str, str] = {}
    if screen:
        texts = {name: han_only("".join(lines)) for name, lines in engine_lines.items()}
        excluded = {k: v for k, v in find_outliers(texts).items() if k != backbone}
        kept = {k: v for k, v in texts.items() if k not in excluded}
        excluded.update(find_order_mismatch(kept, backbone))
        engine_lines = {k: v for k, v in engine_lines.items() if k not in excluded}
    bb_lines = [han_only(line) for line in engine_lines[backbone]]
    bb_lines = [line for line in bb_lines if line]
    bb = "".join(bb_lines)
    line_of = [i for i, line in enumerate(bb_lines) for _ in line]

    others = {name: han_only("".join(lines)) for name, lines in engine_lines.items() if name != backbone}
    others = {name: text for name, text in others.items() if text}
    engines = [backbone, *others]

    char_votes: list[dict[str, list[str]]] = [{bb[i]: [backbone]} for i in range(len(bb))]
    insert_votes: list[dict[str, list[str]]] = [{} for _ in range(len(bb) + 1)]
    for name, text in others.items():
        for tag, i1, i2, j1, j2 in Levenshtein.opcodes(bb, text):
            if tag in ("equal", "replace"):
                for k in range(i2 - i1):
                    char_votes[i1 + k].setdefault(text[j1 + k], []).append(name)
            elif tag == "delete":
                for k in range(i1, i2):
                    char_votes[k].setdefault(NO_CHAR, []).append(name)
            elif tag == "insert":
                insert_votes[i1].setdefault(text[j1:j2], []).append(name)

    if len(engines) < 2:
        slots = [Slot("char", i, bb[i], {bb[i]: [backbone]}, "unaligned", bb[i], None, line_of[i]) for i in range(len(bb))]
        return PageVote(backbone, engines, bb_lines, slots, excluded, "unaligned")

    slots: list[Slot] = []
    out_lines = ["" for _ in bb_lines]
    for i in range(len(bb) + 1):
        ins = insert_votes[i]
        if ins:
            voters = {e for names in ins.values() for e in names}
            votes = {**ins, NO_CHAR: [e for e in engines if e not in voters]}
            status, final, proposal = _decide(NO_CHAR, votes, allow_auto=False)
            line = line_of[i] if i < len(bb) else (line_of[-1] if line_of else 0)
            slots.append(Slot("insert", i, NO_CHAR, votes, status, final, proposal, line))
        if i == len(bb):
            break
        votes = char_votes[i]
        status, final, proposal = _decide(bb[i], votes, allow_auto=True)
        if status == "auto_fixed" and final == NO_CHAR:  # xoá chỉ đề xuất
            status, final, proposal = "suggested", bb[i], NO_CHAR
        slots.append(Slot("char", i, bb[i], votes, status, final, proposal, line_of[i]))
        out_lines[line_of[i]] += final

    return PageVote(
        backbone=backbone, engines=engines, lines=out_lines, slots=slots,
        excluded=excluded, page_status="partial" if excluded else "ok",
    )


def slot_to_dict(slot: Slot) -> dict[str, Any]:
    return {
        "kind": slot.kind,
        "index": slot.index,
        "line": slot.line,
        "backbone": slot.backbone,
        "final": slot.final,
        "proposal": slot.proposal,
        "status": slot.status,
        "votes": slot.votes,
    }


def choose_backbone(texts: dict[str, str], priority: list[str] | tuple[str, ...] = ()) -> str:
    """Chọn engine NỀN sau khi bỏ engine lạc đề: giống các engine còn lại nhất
    (tỉ lệ chữ chung, không phụ thuộc thứ tự). Hoà → engine đọc được NHIỀU chữ
    Hán hơn, rồi mới tới `priority` (vd 2 engine luôn hoà: Phan gia tr.76 —
    Google Vision 21 chữ rác thắng Gemini 326 chữ nếu chỉ xét priority)."""
    texts = {k: v for k, v in texts.items() if v}
    if not texts:
        raise ValueError("Không engine nào có chữ Hán.")
    outliers = find_outliers(texts)
    pool = {k: v for k, v in texts.items() if k not in outliers} or texts
    rank = {name: i for i, name in enumerate(priority)}

    def score(name: str) -> float:
        others = [t for k, t in pool.items() if k != name]
        if not others:
            return 0.0
        text = pool[name]
        return sum(_common(text, t) / max(len(text), len(t)) for t in others) / len(others)

    return min(pool, key=lambda n: (-round(score(n), 6), -len(pool[n]), rank.get(n, len(rank)), n))


def vote_page(engine_lines: dict[str, list[str]], priority: list[str] | tuple[str, ...] = ()) -> PageVote:
    """Hàm chính: engine → các dòng theo thứ tự đọc → kết quả vote (đã sàng engine)."""
    texts = {name: han_only("".join(lines)) for name, lines in engine_lines.items()}
    backbone = choose_backbone(texts, priority)
    return vote_page_chars({k: v for k, v in engine_lines.items() if texts.get(k)}, backbone)


def build_vote_meta(vote: PageVote, engine_lines: dict[str, list[str]]) -> dict[str, Any]:
    """`ocr_vote_meta` schema_version 2 (lưu DB / record). Chỉ giữ vị trí KHÔNG
    nhất trí (`slots`); văn bản kết quả lưu riêng (hannom_text / voted_text)."""
    counts = vote.counts()
    voters = set(vote.engines)
    return {
        "schema_version": 2,
        "vote_method": "char_majority",
        "backbone": vote.backbone,
        "page_status": vote.page_status,
        "thresholds": {"auto_min": AUTO_MIN, "suggest_min": SUGGEST_MIN},
        "stats": {"chars": sum(counts.values()), **dict(counts)},
        "review_rate": round(vote.review_rate(), 4),
        # cùng ý nghĩa "tỉ lệ cần soát" cho giao diện cũ đang đọc uncertain_rate
        "uncertain_rate": round(vote.review_rate(), 4),
        "engines": {
            name: {
                "text": "\n".join(lines),
                "han_chars": len(han_only("".join(lines))),
                "voted": name in voters,
                "excluded": vote.excluded.get(name),
            }
            for name, lines in engine_lines.items()
        },
        # văn bản kết quả theo dòng của nền — để giao diện tô màu từng chữ mà
        # không phụ thuộc hannom_text (có thể bị sửa tay sau này)
        "lines": list(vote.lines),
        "slots": [slot_to_dict(s) for s in vote.slots if s.status != "unanimous"],
    }
