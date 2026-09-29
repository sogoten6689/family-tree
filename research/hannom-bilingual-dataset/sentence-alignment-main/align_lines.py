# -*- coding: utf-8 -*-
"""Ghep 2 file text (Han / Viet) theo NGHIA bang Bertalign (LaBSE), dung cho
truong hop 2 file KHONG khop vi tri dong (khac so dong) — vd rut ra tu file
Word/PDF ma nguoi go xuong dong khac nhau moi cot.

Neu 2 file ĐÃ dam bao dong N ben Han khop dung dong N ben Viet (vd bang
markdown Hop|Han|Dich, hoac dich_nghia.py tung dong) thi KHONG can dung
script nay — chi can zip() truc tiep, nhanh hon va khong co rui ro model
ghep sai.

Dung:
  python3 align_lines.py <file_han.txt> <file_viet.txt> <out_pairs.json>

Moi dong trong file input la 1 don vi de ghep (is_split=True, khong dua
vao dau cau vi Han Nom OCR thuong khong co dau cau).

Can chay voi bien moi truong nay (hoac de align_fix.apply() tu set):
  KMP_DUPLICATE_LIB_OK=TRUE OMP_NUM_THREADS=1 python3 align_lines.py ...
"""
import json
import sys

import align_fix
align_fix.apply()

import bertalign  # noqa: E402  (import SAU align_fix.apply())


def align_files(han_path: str, viet_path: str) -> list[dict]:
    with open(han_path, encoding="utf-8") as f:
        han_lines = [ln.strip() for ln in f if ln.strip()]
    with open(viet_path, encoding="utf-8") as f:
        viet_lines = [ln.strip() for ln in f if ln.strip()]

    print(f"so dong Han: {len(han_lines)} | so dong Viet: {len(viet_lines)}")

    aligner = bertalign.Bertalign(
        src="\n".join(han_lines), tgt="\n".join(viet_lines), is_split=True
    )
    aligner.align_sents()

    pairs = []
    for bead in aligner.result:
        han = aligner._get_line(bead[0], aligner.src_sents)
        viet = aligner._get_line(bead[1], aligner.tgt_sents)
        pairs.append({"han": han, "viet": viet, "align_method": "model", "confidence": "trung_binh"})
    return pairs


def main() -> int:
    if len(sys.argv) != 4:
        print(__doc__)
        return 1
    han_path, viet_path, out_path = sys.argv[1:4]
    pairs = align_files(han_path, viet_path)
    print(f"so cap ghep duoc: {len(pairs)}")
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(pairs, f, ensure_ascii=False, indent=2)
    print(f"da luu: {out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
