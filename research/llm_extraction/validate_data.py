"""Kiểm tra file JSONL dữ liệu gia phả (format Alpaca: Instruction / Input / Response).

Cách dùng:
    python research/llm_extraction/validate_data.py            # train + test tổng hợp mặc định
    python research/llm_extraction/validate_data.py a.jsonl    # kiểm tra file chỉ định
    python research/llm_extraction/validate_data.py --real --quiet-warn <vgp>/train.jsonl <vgp>/test.jsonl

Lỗi (ERROR) làm mẫu bị tính là không hợp lệ; cảnh báo (WARN) chỉ in ra.
Mã thoát = 1 nếu có ít nhất một mẫu lỗi.
"""
import argparse
import json
import re
import sys
from pathlib import Path

from _paths import SYNTH_DIR

DEFAULT_FILES = [SYNTH_DIR / "giapha_train.jsonl", SYNTH_DIR / "giapha_test.jsonl"]

MARK_INSTR, MARK_INPUT, MARK_RESP = "### Instruction:\n", "### Input:\n", "### Response:\n"
REL_TYPES = {"spouse", "father", "mother", "son", "daughter"}
PERSON_FIELDS = {"name", "birth", "death", "generation", "gender"}


def split_text(text):
    """Trả về (instruction, input, response) hoặc ném ValueError."""
    for m in (MARK_INSTR, MARK_INPUT, MARK_RESP):
        if text.count(m) != 1:
            raise ValueError(f"thiếu hoặc lặp phần '{m.strip()}' (xuất hiện {text.count(m)} lần)")
    i0, i1, i2 = text.index(MARK_INSTR), text.index(MARK_INPUT), text.index(MARK_RESP)
    if not (i0 == 0 and i0 < i1 < i2):
        raise ValueError("thứ tự phải là Instruction -> Input -> Response, bắt đầu bằng Instruction")
    instr = text[len(MARK_INSTR):i1].strip()
    inp = text[i1 + len(MARK_INPUT):i2].strip()
    resp = text[i2 + len(MARK_RESP):].strip()
    for label, val in (("Instruction", instr), ("Input", inp), ("Response", resp)):
        if not val:
            raise ValueError(f"phần {label} rỗng")
    return instr, inp, resp


def is_year(v):
    return v is None or (isinstance(v, int) and not isinstance(v, bool) and 1000 <= v <= 2100)


def check_answer(ans, inp, strict=True):
    errors, warns = [], []
    if not isinstance(ans, dict) or set(ans) != {"persons", "relations"}:
        return [f"Response phải là object có đúng 2 khóa persons, relations (đang có {list(ans) if isinstance(ans, dict) else type(ans).__name__})"], warns
    persons, rels = ans["persons"], ans["relations"]
    if not isinstance(persons, list) or (strict and not persons):
        errors.append("persons phải là list" + (" không rỗng" if strict else ""))
        persons = []
    if not isinstance(rels, list):
        errors.append("relations phải là list")
        rels = []

    gender = {}
    for k, p in enumerate(persons):
        tag = f"persons[{k}]"
        if not isinstance(p, dict):
            errors.append(f"{tag} không phải object")
            continue
        miss, extra = PERSON_FIELDS - set(p), set(p) - PERSON_FIELDS
        if miss:
            errors.append(f"{tag} thiếu field {sorted(miss)}")
        if extra:
            errors.append(f"{tag} thừa field {sorted(extra)}")
        name = p.get("name")
        if not isinstance(name, str) or len(name.split()) < 2:
            errors.append(f"{tag} name phải là họ tên đầy đủ (>= 2 tiếng): {name!r}")
            continue
        if name not in inp:
            warns.append(f"{tag} tên '{name}' không xuất hiện nguyên văn trong Input")
        for f in ("birth", "death"):
            if f in p and not is_year(p[f]):
                errors.append(f"{tag} {f} phải là số năm hoặc null: {p[f]!r}")
        b, d = p.get("birth"), p.get("death")
        if isinstance(b, int) and isinstance(d, int) and d < b:
            errors.append(f"{tag} '{name}' mất ({d}) trước khi sinh ({b})")
        g = p.get("generation")
        if g is not None and (not isinstance(g, int) or isinstance(g, bool) or g < 1):
            errors.append(f"{tag} generation phải là số nguyên >= 1 hoặc null: {g!r}")
        if p.get("gender") not in ("male", "female", None):
            errors.append(f"{tag} gender phải là male/female hoặc null: {p.get('gender')!r}")
        gender.setdefault(name, set()).add(p.get("gender"))
    if strict and persons and not any(isinstance(p, dict) and p.get("generation") == 1 for p in persons):
        errors.append("không có người nào ở generation 1 (cụ tổ)")
    n_null = sum(1 for p in persons if isinstance(p, dict) and (p.get("generation") is None or p.get("gender") is None))
    if strict and n_null:
        errors.append(f"{n_null} người thiếu generation/gender (dữ liệu tổng hợp phải đủ)")

    def gset(n):
        return gender.get(n, set())

    parents_of, spouses = {}, {}
    for k, r in enumerate(rels):
        tag = f"relations[{k}]"
        if not isinstance(r, dict) or set(r) != {"from", "to", "type"}:
            errors.append(f"{tag} phải có đúng 3 field from, to, type: {r!r}")
            continue
        a, b, t = r["from"], r["to"], r["type"]
        if t not in REL_TYPES:
            errors.append(f"{tag} type '{t}' không thuộc {sorted(REL_TYPES)}")
            continue
        for n in (a, b):
            if n not in gender:
                errors.append(f"{tag} tên '{n}' không có trong persons")
        if a == b:
            errors.append(f"{tag} from và to trùng nhau: '{a}'")
        if t == "father" and "male" not in gset(a):
            errors.append(f"{tag} father nhưng '{a}' không phải male")
        if t == "mother" and "female" not in gset(a):
            errors.append(f"{tag} mother nhưng '{a}' không phải female")
        if t == "son" and "male" not in gset(a):
            errors.append(f"{tag} son nhưng '{a}' không phải male")
        if t == "daughter" and "female" not in gset(a):
            errors.append(f"{tag} daughter nhưng '{a}' không phải female")
        if t in ("father", "mother"):
            parents_of.setdefault(b, {})[t] = a
        if t == "spouse":
            spouses.setdefault(a, set()).add(b)
            spouses.setdefault(b, set()).add(a)

    rel_set = {(r["from"], r["to"], r["type"]) for r in rels if isinstance(r, dict) and set(r) == {"from", "to", "type"}}
    for child, par in parents_of.items():
        # Quy tắc: A là cha của C và A chỉ có 1 vợ B -> phải có B mẹ của C
        fa = par.get("father")
        if fa and "mother" not in par and len(spouses.get(fa, set())) == 1:
            wife = next(iter(spouses[fa]))
            (errors if strict else warns).append(f"'{fa}' father của '{child}' nhưng thiếu '{wife}' (vợ duy nhất) mother của '{child}'")
        for t, p in par.items():
            inv = "son" if "male" in gset(child) else "daughter"
            if (child, p, inv) not in rel_set:
                warns.append(f"thiếu quan hệ ngược '{child}' -> '{p}' ({inv})")

    n_sent = len([s for s in re.split(r"[.!?]\s+|[.!?]$", inp) if s.strip()])
    if strict and not 3 <= n_sent <= 6:
        warns.append(f"Input có {n_sent} câu (yêu cầu 3-6)")
    return errors, warns


def validate_file(path, strict=True, quiet_warn=False):
    ok, bad, inputs = 0, 0, []
    n_warn_total = [0]
    print(f"\n=== {path} ===" + ("" if strict else " (chế độ dữ liệu thật: cho phép null, quy tắc cha-mẹ chỉ cảnh báo)"))
    if not path.exists():
        print(f"ERROR: không tìm thấy file")
        return 0, 1, inputs
    with open(path, encoding="utf-8") as fh:
        for lineno, line in enumerate(fh, 1):
            if not line.strip():
                print(f"[dòng {lineno}] ERROR: dòng trống")
                bad += 1
                continue
            errors, warns = [], []
            try:
                rec = json.loads(line)
            except json.JSONDecodeError as e:
                errors.append(f"JSON lỗi: {e}")
                rec = None
            inp = None
            if rec is not None:
                if not isinstance(rec, dict) or "text" not in rec:
                    errors.append("thiếu field 'text'")
                elif not isinstance(rec["text"], str):
                    errors.append("'text' phải là chuỗi")
                else:
                    if set(rec) - {"text", "meta"}:
                        warns.append(f"có field thừa ngoài 'text'/'meta': {sorted(set(rec) - {'text', 'meta'})}")
                    try:
                        _, inp, resp = split_text(rec["text"])
                        try:
                            ans = json.loads(resp)
                            e2, w2 = check_answer(ans, inp, strict)
                            errors += e2
                            warns += w2
                        except json.JSONDecodeError as e:
                            errors.append(f"Response không phải JSON hợp lệ: {e}")
                    except ValueError as e:
                        errors.append(str(e))
            n_warn_total[0] += len(warns)
            for w in ([] if quiet_warn else warns):
                print(f"[dòng {lineno}] WARN: {w}")
            for e in errors:
                print(f"[dòng {lineno}] ERROR: {e}")
            if errors:
                bad += 1
            else:
                ok += 1
            if inp:
                inputs.append((lineno, inp))
    seen = {}
    for lineno, inp in inputs:
        if inp in seen:
            print(f"[dòng {lineno}] WARN: Input trùng với dòng {seen[inp]}")
        seen.setdefault(inp, lineno)
    print(f"--> hợp lệ: {ok} | lỗi: {bad} | tổng: {ok + bad} | cảnh báo: {n_warn_total[0]}")
    return ok, bad, inputs


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("files", nargs="*", type=Path, default=DEFAULT_FILES)
    ap.add_argument("--real", action="store_true",
                    help="dữ liệu thật (VGP): cho phép generation/gender null, persons rỗng; quy tắc cha-mẹ chỉ cảnh báo")
    ap.add_argument("--quiet-warn", action="store_true", help="không in từng cảnh báo, chỉ in tổng")
    args = ap.parse_args()
    total_bad, all_inputs = 0, {}
    for f in args.files:
        _, bad, inputs = validate_file(f, strict=not args.real, quiet_warn=args.quiet_warn)
        total_bad += bad
        all_inputs[f] = {inp for _, inp in inputs}
    if len(args.files) >= 2:
        a, b = args.files[0], args.files[1]
        overlap = all_inputs[a] & all_inputs[b]
        print(f"\nTrùng Input giữa {a.name} và {b.name}: {len(overlap)} mẫu")
        if overlap:
            total_bad += len(overlap)
    sys.exit(1 if total_bad else 0)


if __name__ == "__main__":
    main()
