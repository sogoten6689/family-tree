"""Bộ song song sạch của nhóm sách chưa giao cho sinh viên (lab tự làm), để người hướng dẫn xem và tải.

Tách hai phần, không trộn:
- "da_soat": các trang người soát đã xác nhận trong thẻ Soát (soat_nhap.json → da_soat), đúng quy tắc của nút Nộp
  (soat.build_tsv). Chưa có nháp thì lấy TSV đã nộp.
- "may": các trang còn lại, lấy từ nháp (nếu có) hoặc bản máy cap_cau.csv; chỉ làm sạch định dạng, chưa người soát.

Làm sạch: phần máy bỏ ghi chú của người dịch máy trong ngoặc ("(không chắc)", "(bản gốc ghi …)"…); gộp xuống dòng/tab trong ô, bỏ cặp thiếu vế, vế Hán không có chữ Hán, vế Việt lẫn chữ Hán
(sau khi thử bỏ chữ Hán trong ngoặc), và cặp trùng (kể cả trùng với phần đã soát).
Phần máy áp chữ "đề xuất sửa" của vote (đa số ≥ 2 phiếu trên tổng ≥ 3 chọn chữ khác chữ nền; anh Lâm chốt
18/11/2026). Chỉ áp khi tìm được đúng một chỗ của dòng nền (hoặc đoạn quanh chữ) trong các cặp cùng trang.
Phần đã soát không áp: chữ người soát được giữ nguyên.
"""
from __future__ import annotations

import re
from functools import lru_cache
from pathlib import Path

from app.doi_chieu import service, soat, vote

GROUP = "chua-giao"
KINDS = ("da-soat", "may")
_HAN_IN_PARENS = re.compile(r"\s*[（(][^（）()]*[㐀-鿿\U00020000-\U0003134f][^（）()]*[）)]")


# Ghi chú của người dịch máy (không phải nội dung dịch): "(không chắc)", "(bản gốc ghi …)", "(hoặc …)"…
# Chú giải nghĩa như "(mẹ)", "(chết yểu)", "(Giáp Thìn)" vẫn giữ. Anh Lâm chốt bỏ ghi chú 17/11/2026.
_NOTE_WORDS = re.compile(
    r"không chắc|không rõ|chưa rõ|bản gốc|nguyên văn|khả năng|có thể|hoặc|nhầm|khuyết|thoát chữ|ghi sai|chép sai|\?",
    re.IGNORECASE,
)
_PAREN = re.compile(r"\s*[（(]([^（）()]*(?:[（(][^（）()]*[）)][^（）()]*)*)[）)]")
_BRACKET = re.compile(r"\s*\[([^\[\]]*(?:\[[^\[\]]*\][^\[\]]*)*)\]")
_DANGLING = re.compile(r"\s*[-–]\s*không chắc\)?", re.IGNORECASE)
_SPACE_BEFORE_PUNCT = re.compile(r"\s+([,.;:!?…])")
_DOUBLE_PUNCT = re.compile(r"([,;:])\s*(?=[,.;:])")


def _has_note(viet: str) -> bool:
    groups = [*_PAREN.finditer(viet), *_BRACKET.finditer(viet)]
    return any(_NOTE_WORDS.search(m.group(1)) for m in groups) or bool(_DANGLING.search(viet))


def _drop_notes(viet: str) -> str:
    drop = lambda m: "" if _NOTE_WORDS.search(m.group(1)) else m.group(0)  # noqa: E731
    out = _BRACKET.sub(drop, _PAREN.sub(drop, viet))
    out = _DANGLING.sub("", out)
    out = _SPACE_BEFORE_PUNCT.sub(r"\1", out)
    out = _DOUBLE_PUNCT.sub("", out)
    return " ".join(out.split()).strip(" ,;:")


def _clean_viet(viet: str) -> str:
    viet = _drop_notes(viet)
    return _HAN_IN_PARENS.sub("", viet).strip() if service.HAN_RE.search(viet) else viet


def _choice(c: dict) -> str | None:
    """Chữ thay: chữ khác chữ nền có nhiều phiếu nhất; hoà thì bỏ qua."""
    ranked = sorted(((n, ch) for ch, n in (c.get("phieu") or {}).items() if ch != c.get("nen")), reverse=True)
    if not ranked or (len(ranked) > 1 and ranked[0][0] == ranked[1][0]):
        return None
    return ranked[0][1]


def _han_positions(text: str) -> list[int]:
    """Vị trí trong chuỗi gốc của từng chữ Hán (bỏ dấu câu, khoảng trắng)."""
    return [i for i, ch in enumerate(text) if service.HAN_RE.fullmatch(ch)]


MIN_LINE = 6
# Nhóm chữ dễ nhầm hình mà chữ nào cũng thông dụng: máy hay đồng loạt đọc nhầm sang nhau, chữ nền thường
# đúng theo ngữ cảnh (毋叨/母, 謫戍/戌, 不得已/己, 壬戌/七). Không tự áp, để người soát xem ảnh.
_CONFUSABLE = [set(g) for g in ("已己巳", "戍戌戊", "毋母", "日曰", "未末", "土士", "人入八", "大太犬", "千干于午", "壬七王", "子孑", "刀力")]


def _confusable(a: str, b: str) -> bool:
    return any(a in g and b in g for g in _CONFUSABLE)


def _apply_votes(rows: list[dict], pages: list[dict] | None) -> tuple[list[dict], int, int, int]:
    """Áp chữ đề xuất sửa vào các cặp máy. Trả về (cặp mới, đã áp, không tìm được chỗ, bỏ vì nghi ghép lệch)."""
    if not pages:
        return rows, 0, 0, 0
    orig = [r.get("han") or "" for r in rows]  # tìm chỗ trên bản gốc; thay 1 chữ nên vị trí không lệch
    rows = [dict(r) for r in rows]
    by_page: dict[str, list[int]] = {}
    for idx, r in enumerate(rows):
        by_page.setdefault(r.get("trang", ""), []).append(idx)
    applied = missed = skipped = 0
    for page in pages:
        idxs = by_page.get(page.get("page_id", ""), [])
        if not idxs:
            continue  # trang đã soát (hoặc không có cặp máy): không áp, không tính là không khớp
        for line in page.get("dong") or []:
            for c in line.get("chu") or []:
                if c.get("kq") != "de_xuat_sua":
                    continue
                new = _choice(c)
                text, i = line.get("nen") or "", c.get("vi_tri", -1)
                if new is None or not (0 <= i < len(text)) or text[i] != c.get("nen"):
                    missed += 1
                    continue
                # Dòng ngắn (sơ đồ cây, tên lặp "…公次子") hay ghép lệch một vị trí: chữ đề xuất là chữ bên cạnh;
                # cặp dễ nhầm hình cũng không tự áp.
                if len(text) < MIN_LINE or new in text[max(0, i - 2) : i + 3] or _confusable(c["nen"], new):
                    skipped += 1
                    continue
                target = None
                for lo, hi in ((0, len(text)), (max(0, i - 3), i + 4)):
                    probe = text[lo:hi]
                    hits = []
                    for idx in idxs:
                        han = service.han_only(orig[idx])
                        start = han.find(probe)
                        if start >= 0 and han.find(probe, start + 1) < 0:
                            hits.append((idx, start + i - lo))
                        elif start >= 0:
                            hits.append((idx, -1))  # nhiều chỗ trong một cặp: không chắc chỗ nào
                    if len(hits) == 1 and hits[0][1] >= 0:
                        target = hits[0]
                        break
                if target is None:
                    missed += 1
                    continue
                idx, k = target
                pos = _han_positions(orig[idx])[k]
                raw = rows[idx]["han"]
                if orig[idx][pos] != c["nen"]:
                    missed += 1
                    continue
                rows[idx]["han"] = raw[:pos] + new + raw[pos + 1 :]
                applied += 1
    return rows, applied, missed, skipped


def _signature(bdir: Path) -> tuple:
    files = [bdir / "cap_cau.csv", bdir / soat.DRAFT_NAME, bdir / vote.FILE_NAME, *sorted(bdir.glob("*.tsv"))]
    return tuple((f.name, f.stat().st_mtime_ns, f.stat().st_size) for f in files if f.is_file())


@lru_cache(maxsize=64)
def _build(bdir_str: str, signature: tuple) -> dict:
    bdir = Path(bdir_str)
    draft = soat._read_draft(bdir)
    if draft is not None:
        reviewed_rows, _ = soat.build_tsv(draft, soat.machine_gutters(bdir))
        confirmed = set(draft["da_soat"])
        rest = [r for r in draft["rows"] if r["trang"] not in confirmed and not r["bo"]]
    else:
        tsv = service.load_book(bdir)["tsv"]
        reviewed_rows = (
            [{"trang": "", "han": p.han, "viet": p.viet} for p in service.parse_tsv((bdir / tsv).read_text(encoding="utf-8"))]
            if tsv
            else []
        )
        confirmed = set()
        rest = [] if tsv else service.read_machine(bdir / "cap_cau.csv")

    seen: set[tuple[str, str]] = set()
    dropped = {"thieu_ve": 0, "han_khong_co_chu_han": 0, "viet_lan_chu_han": 0, "trung": 0}
    notes_removed = 0

    def clean(rows: list[dict], fix_viet: bool) -> list[tuple[str, str]]:
        out = []
        for r in rows:
            han, viet = soat._clean_cell(r.get("han") or ""), soat._clean_cell(r.get("viet") or "")
            if fix_viet:
                cleaned = _clean_viet(viet)
                if _has_note(viet):
                    nonlocal notes_removed
                    notes_removed += 1
                viet = cleaned
            if not han or not viet:
                dropped["thieu_ve"] += 1
            elif not service.HAN_RE.search(han):
                dropped["han_khong_co_chu_han"] += 1
            elif service.HAN_RE.search(viet):
                dropped["viet_lan_chu_han"] += 1
            elif (han, viet) in seen:
                dropped["trung"] += 1
            else:
                seen.add((han, viet))
                out.append((han, viet))
        return out

    # Phần đã soát giữ nguyên chữ người soát, chỉ bỏ dòng sai định dạng/trùng.
    reviewed = clean(reviewed_rows, fix_viet=False)
    rest, vote_applied, vote_missed, vote_skipped = _apply_votes(rest, vote.pages(bdir))
    machine = clean(rest, fix_viet=True)
    pages = {r["trang"] for r in (draft["rows"] if draft else service.read_machine(bdir / "cap_cau.csv"))}
    return {
        "summary": {
            "da_soat": len(reviewed),
            "may": len(machine),
            "trang": len(pages),
            "trang_da_soat": len(confirmed & pages),
            "bo": dropped,
            "bo_ghi_chu": notes_removed,
            "sua_vote": vote_applied,
            "sua_vote_khong_khop": vote_missed,
            "sua_vote_nghi_lech": vote_skipped,
        },
        "da-soat": "".join(f"{h}\t{v}\n" for h, v in reviewed),
        "may": "".join(f"{h}\t{v}\n" for h, v in machine),
    }


def build(bdir: Path) -> dict | None:
    if bdir.parent.name != GROUP or not (bdir / "cap_cau.csv").is_file():
        return None
    return _build(str(bdir), _signature(bdir))


def summary(bdir: Path) -> dict | None:
    built = build(bdir)
    return built["summary"] if built else None


def tsv(bdir: Path, kind: str) -> str | None:
    built = build(bdir)
    return built[kind] if built and kind in KINDS else None
