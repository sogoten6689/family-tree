"""Tạo từ điển âm Hán Việt từng chữ cho trang Đối chiếu: <DOI_CHIEU_DIR>/han_viet.json (xem app/doi_chieu/am_han_viet.py).

Nguồn (tải về máy, không đưa vào repo):
- thieuchuu.txt, phienam.txt: https://github.com/ryanphung/chinese-hanviet-cognates (thư mục inputs/). thieuchuu.txt là
  Hán Việt tự điển của Thiều Chửu, mỗi dòng "chữ=âm1, âm2 [pinyin]\\n...nghĩa"; chỉ lấy phần âm. phienam.txt bổ sung chữ thiếu.
- Unihan_Variants.txt: https://www.unicode.org/Public/UCD/latest/ucd/Unihan.zip, để tra âm qua chữ dị thể/giản/phồn.

Chữ có nhiều âm được xếp lại theo số cặp trong kho đối chiếu mà vế Việt có âm đó (ví dụ 生: "sinh" trước "sanh"),
không đếm tên can chi; hoà thì giữ thứ tự của từ điển; vài chữ đặt âm trước theo PREFERRED. Khi hiển thị, âm có trong
vế Việt của chính cặp được chọn trước (am_han_viet.phien_am), ngoài ra vẫn là tra từng chữ, không theo ngữ cảnh.

    python nlp_family_extractor/tools/tao_tu_dien_han_viet.py --thieu-chuu thieuchuu.txt --phien-am phienam.txt \\
        --unihan Unihan_Variants.txt --kho <DOI_CHIEU_DIR> [--ra <DOI_CHIEU_DIR>/han_viet.json]
"""
from __future__ import annotations

import argparse
import csv
import json
import re
from collections import Counter
from pathlib import Path

HAN_RE = re.compile(r"[㐀-䶿一-鿿豈-﫿\U00020000-\U0003ffff]")
WORD_RE = re.compile(r"[^\W\d_]+")
VARIANT_FIELDS = ("kTraditionalVariant", "kSimplifiedVariant", "kZVariant", "kSemanticVariant", "kSpecializedSemanticVariant")
# Dạng chữ Nhật/khắc in hay gặp trong kho mà Unihan không nối về chữ phồn thể có trong Thiều Chửu.
EXTRA_VARIANTS = {
    "帰": "歸", "淸": "清", "劔": "劍", "経": "經", "継": "繼", "豊": "豐", "尓": "爾", "乗": "乘", "曽": "曾",
    "眀": "明", "楽": "樂", "靑": "青", "垕": "厚", "僡": "惠", "曤": "曜",
}


# Vế Việt ghi năm/giờ theo can chi ("năm Mậu Tuất", "giờ Tý") nên đếm các âm này sẽ kéo 子 thành "tý", 卒 thành "tuất".
# Bỏ khỏi phần đếm; khi hiển thị, âm can chi vẫn được chọn nếu vế Việt của chính cặp đó có (xem app/doi_chieu/am_han_viet.py).
CYCLICAL = set("giáp ất bính đinh mậu kỷ kỉ canh tân nhâm quý quí tý tí sửu dần mão mẹo thìn tỵ tị ngọ mùi thân dậu tuất hợi".split())
# Âm đặt trước sau khi xếp, cho chữ hay gặp mà đếm theo kho vẫn chọn sai (soát 18/11/2026).
PREFERRED = {"行": "hành", "妻": "thê", "的": "đích", "食": "thực", "适": "thích", "子": "tử", "卒": "tốt"}


def _norm(reading: str) -> str:
    # Bản số hoá Thiều Chửu dùng Ð (U+00D0, chữ Iceland) thay cho Đ.
    return reading.replace("Ð", "Đ").replace("ð", "đ").strip().lower()


def read_thieu_chuu(path: Path) -> dict[str, list[str]]:
    out: dict[str, list[str]] = {}
    for line in path.read_text(encoding="utf-8-sig").splitlines():
        ch, sep, rest = line.partition("=")
        if not sep or len(ch) != 1:
            continue
        head = rest.split("[")[0].split("\\n")[0]
        readings = [r for r in (_norm(x) for x in head.split(",")) if r and WORD_RE.fullmatch(r)]
        if readings:
            # Có chữ có hai mục (适 = quát; 适 = thích, đích): gộp âm, giữ thứ tự gặp.
            out[ch] = list(dict.fromkeys([*out.get(ch, []), *readings]))
    return out


def read_phien_am(path: Path) -> dict[str, list[str]]:
    out: dict[str, list[str]] = {}
    for line in path.read_text(encoding="utf-8-sig").splitlines():
        ch, sep, reading = line.partition("=")
        reading = _norm(reading)
        if sep and len(ch) == 1 and reading and WORD_RE.fullmatch(reading):
            out.setdefault(ch, [reading])
    return out


def read_variants(path: Path) -> dict[str, list[str]]:
    out: dict[str, list[str]] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        parts = line.split("\t")
        if len(parts) == 3 and parts[1] in VARIANT_FIELDS:
            src = chr(int(parts[0][2:], 16))
            for item in parts[2].split():
                out.setdefault(src, []).append(chr(int(item.split("<")[0][2:], 16)))
    return out


def corpus_pairs(root: Path) -> list[tuple[str, str]]:
    pairs = []
    for csv_path in sorted(root.glob("*/*/cap_cau.csv")):
        with csv_path.open(encoding="utf-8-sig", newline="") as f:
            pairs += [(r.get("han") or "", r.get("viet_may") or "") for r in csv.DictReader(f)]
        retranslated = csv_path.parent / "dich_lai.json"
        if retranslated.is_file():
            pairs += list(json.loads(retranslated.read_text(encoding="utf-8")).items())
    return pairs


def build(base: dict[str, list[str]], extra: dict[str, list[str]], variants: dict[str, list[str]], pairs: list[tuple[str, str]]) -> dict:
    table = dict(extra)
    table.update(base)
    borrowed: dict[str, str] = {}
    for ch, targets in [*variants.items(), *((k, [v]) for k, v in EXTRA_VARIANTS.items())]:
        if ch not in table:
            hit = next((t for t in targets if t in table), None)
            if hit:
                table[ch] = list(table[hit])
                borrowed[ch] = hit

    votes: dict[str, Counter] = {}
    for han, viet in pairs:
        words = set(WORD_RE.findall(viet.lower()))
        for ch in set(han):
            readings = table.get(ch)
            if readings and len(readings) > 1:
                counter = votes.setdefault(ch, Counter())
                counter.update(r for r in readings if r in words and r not in CYCLICAL)
    for ch, counter in votes.items():
        order = table[ch]
        table[ch] = sorted(order, key=lambda r: (-counter[r], order.index(r)))
    for ch, first in PREFERRED.items():
        if ch in table and first in table[ch]:
            table[ch] = [first, *(r for r in table[ch] if r != first)]
    # Dị thể không có trong kho thì theo thứ tự đã xếp của chữ gốc.
    for ch, hit in borrowed.items():
        if not votes.get(ch):
            table[ch] = list(table[hit])
    return dict(sorted(table.items()))


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--thieu-chuu", type=Path, required=True)
    parser.add_argument("--phien-am", type=Path, required=True)
    parser.add_argument("--unihan", type=Path, required=True, help="Unihan_Variants.txt")
    parser.add_argument("--kho", type=Path, required=True, help="thư mục DOI_CHIEU_DIR (đọc <nhóm>/<cuốn>/cap_cau.csv)")
    parser.add_argument("--ra", type=Path, help="mặc định <kho>/han_viet.json")
    args = parser.parse_args()

    pairs = corpus_pairs(args.kho)
    table = build(read_thieu_chuu(args.thieu_chuu), read_phien_am(args.phien_am), read_variants(args.unihan), pairs)
    out = args.ra or args.kho / "han_viet.json"
    out.write_text(json.dumps(table, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")

    chars = Counter(ch for han, _ in pairs for ch in han if HAN_RE.fullmatch(ch))
    known = sum(n for ch, n in chars.items() if ch in table)
    total = sum(chars.values())
    print(f"{len(table)} chữ trong từ điển; kho có {total} lượt chữ Hán, tra được {known} ({known / total:.2%})" if total else f"{len(table)} chữ")


if __name__ == "__main__":
    main()
