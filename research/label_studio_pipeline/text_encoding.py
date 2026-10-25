"""Phát hiện và sửa Phả ký ở bảng mã tiếng Việt cũ (TCVN3/ABC, VNI-Windows) bị đọc như CP1252.

Sửa TỪNG DÒNG (tài liệu có thể trộn Unicode/TCVN3/VNI): dòng có ký tự đánh dấu → chọn bản (giữ / TCVN3 / VNI) có độ phủ
từ vựng cao nhất; dòng không có ký tự đánh dấu giữ nguyên. Từ vựng = âm tiết xuất hiện ≥3 lần trong các Phả ký sạch.
Kiểm 25/10/2026 trên 342 cây gia_pha: 23 cây lỗi mã, 18 sửa được (độ phủ từ vựng → 0,89–1,00), không dòng Unicode nào bị đổi.
TCVN3 đổi 1 ký tự → 1 ký tự (giữ offset); VNI gộp 2 ký tự → 1 (làm lệch offset nhãn).
"""

from __future__ import annotations

import re
import unicodedata
from collections import Counter
from typing import Iterable

# Ký tự không có trong tiếng Việt Unicode (chữ hoa Ã, À, Õ… hợp lệ như ĐOÃN, HOÀNG nên không dùng) + cặp VNI "OÂ/AÂ/EÂ"
LEGACY_MARK = re.compile(r"[®¬µ¸¹¶·¨©ª«¤¥¦§¢£¡¿×ØÜÞßøçæëïîäåûüþñö]|[ÄÅÆÇËÎÏÑÖÛ]|[AEO]Â")
SYLLABLE = re.compile(r"[^\W\d_]+", re.UNICODE)
DETECT_THRESHOLD = 0.002  # tỉ lệ ký tự đánh dấu; cây sạch ≈ 0

TCVN3 = {
    "µ": "à", "¸": "á", "¶": "ả", "·": "ã", "¹": "ạ",
    "¨": "ă", "»": "ằ", "¾": "ắ", "¼": "ẳ", "½": "ẵ", "Æ": "ặ",
    "©": "â", "Ç": "ầ", "Ê": "ấ", "È": "ẩ", "É": "ẫ", "Ë": "ậ",
    "®": "đ", "Ì": "è", "Ð": "é", "Î": "ẻ", "Ï": "ẽ", "Ñ": "ẹ",
    "ª": "ê", "Ò": "ề", "Õ": "ế", "Ó": "ể", "Ô": "ễ", "Ö": "ệ",
    "×": "ì", "Ý": "í", "Ø": "ỉ", "Ü": "ĩ", "Þ": "ị",
    "ß": "ò", "ã": "ó", "á": "ỏ", "â": "õ", "ä": "ọ",
    "«": "ô", "å": "ồ", "è": "ố", "æ": "ổ", "ç": "ỗ", "é": "ộ",
    "¬": "ơ", "ê": "ờ", "í": "ớ", "ë": "ở", "ì": "ỡ", "î": "ợ",
    "ï": "ù", "ó": "ú", "ñ": "ủ", "ò": "ũ", "ô": "ụ",
    "­": "ư", "õ": "ừ", "ø": "ứ", "ö": "ử", "÷": "ữ", "ù": "ự",
    "ú": "ỳ", "ý": "ý", "û": "ỷ", "ü": "ỹ", "þ": "ỵ",
    "§": "Đ", "¡": "Ă", "¢": "Â", "£": "Ê", "¤": "Ô", "¥": "Ơ", "¦": "Ư",
}
_TCVN3_TABLE = str.maketrans(TCVN3)

# VNI-Windows: chữ gốc + ký tự dấu đi sau; ơ = ô, ư = ö (đứng riêng); i có mã riêng (æ ó ò)
_TONE = {"ø": "̀", "ù": "́", "û": "̉", "õ": "̃", "ï": "̣"}
_CIRC_TONE = {"à": "̀", "á": "́", "å": "̉", "ã": "̃", "ä": "̣"}
_BREVE_TONE = {"è": "̀", "é": "́", "ú": "̉", "ü": "̃", "ë": "̣"}
_SINGLE = {"ö": "ư", "ô": "ơ", "ñ": "đ", "æ": "ỉ", "ó": "ĩ", "ò": "ị"}


def _with_upper(d: dict[str, str]) -> dict[str, str]:
    return {**d, **{k.upper(): v.upper() if len(v) == 1 and v.isalpha() else v for k, v in d.items()}}


_TONE_B, _CIRC_B, _BREVE_B, _SINGLE_B = (_with_upper(d) for d in (_TONE, _CIRC_TONE, _BREVE_TONE, _SINGLE))


def tcvn3_to_unicode(text: str) -> str:
    return text.translate(_TCVN3_TABLE)


def vni_to_unicode(text: str) -> str:
    s = re.sub(r"([aeoAEO])([àáåãäÀÁÅÃÄ])", lambda m: m.group(1) + "̂" + _CIRC_B[m.group(2)], text)
    s = re.sub(r"([aA])([èéúüëÈÉÚÜË])", lambda m: m.group(1) + "̆" + _BREVE_B[m.group(2)], s)
    s = re.sub(r"([aeoAEO])([âÂ])", lambda m: m.group(1) + "̂", s)
    s = re.sub(r"([aA])([êÊ])", lambda m: m.group(1) + "̆", s)
    s = re.sub(r"[öôñæóòÖÔÑÆÓÒ]", lambda m: _SINGLE_B[m.group(0)], s)
    s = re.sub(r"([aeiouyAEIOUYăâêôơưĂÂÊÔƠƯ̂̆])([øùûõïØÙÛÕÏ])", lambda m: m.group(1) + _TONE_B[m.group(2)], s)
    return unicodedata.normalize("NFC", s)


def needs_fix(text: str) -> bool:
    return len(LEGACY_MARK.findall(text)) / max(1, len(text)) > DETECT_THRESHOLD


def build_vocab(clean_texts: Iterable[str], min_count: int = 3) -> set[str]:
    counts = Counter(w.lower() for t in clean_texts for w in SYLLABLE.findall(t))
    return {w for w, c in counts.items() if c >= min_count}


def vocab_coverage(text: str, vocab: set[str]) -> float:
    toks = [t.lower() for t in SYLLABLE.findall(text)]
    return sum(t in vocab for t in toks) / max(1, len(toks))


def _fix_line(line: str, vocab: set[str]) -> tuple[str, str]:
    if not LEGACY_MARK.search(line):
        return line, "unicode"
    base = vocab_coverage(line, vocab)
    cands = {"tcvn3": tcvn3_to_unicode(line), "vni": vni_to_unicode(line)}
    best = max(cands, key=lambda k: vocab_coverage(cands[k], vocab))
    return (cands[best], best) if vocab_coverage(cands[best], vocab) > base else (line, "unicode")


def fix_text(text: str, vocab: set[str]) -> tuple[str, dict]:
    """Trả (văn bản đã sửa, báo cáo). Không đổi gì nếu tài liệu không bị phát hiện lỗi mã."""
    before = vocab_coverage(text, vocab)
    if not needs_fix(text):
        return text, {"detected": "unicode"}
    out, used = [], Counter()
    for line in text.split("\n"):
        fixed, how = _fix_line(line, vocab)
        out.append(fixed)
        if how != "unicode":
            used[how] += 1
    new = "\n".join(out)
    return new, {
        "detected": "legacy",
        "fixed_lines": dict(used),
        "vocab_coverage_before": round(before, 4),
        "vocab_coverage_after": round(vocab_coverage(new, vocab), 4),
        "length_changed": len(new) != len(text),
    }
