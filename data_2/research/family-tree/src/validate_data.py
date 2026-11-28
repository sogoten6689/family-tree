"""Kiểm tra file JSONL dữ liệu gia phả (format Alpaca: Instruction / Input / Response).

Cách dùng:
    python src/validate_data.py                       # kiểm tra cả train và test mặc định
    python src/validate_data.py data_train/x.jsonl    # kiểm tra file chỉ định

Lỗi (ERROR) làm mẫu bị tính là không hợp lệ; cảnh báo (WARN) chỉ in ra.
Mã thoát = 1 nếu có ít nhất một mẫu lỗi.
"""
import argparse
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_FILES = [ROOT / "data_train" / "giapha_train.jsonl", ROOT / "data_train" / "giapha_test.jsonl"]

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


def check_answer(ans, inp):
    errors, warns = [], []
    if not isinstance(ans, dict) or set(ans) != {"persons", "relations"}:
        return [f"Response phải là object có đúng 2 khóa persons, relations (đang có {list(ans) if isinstance(ans, dict) else type(ans).__name__})"], warns
    persons, rels = ans["persons"], ans["relations"]
    if not isinstance(persons, list) or not persons:
        errors.append("persons phải là list không rỗng")
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
        if not isinstance(g, int) or isinstance(g, bool) or g < 1:
            errors.append(f"{tag} generation phải là số nguyên >= 1: {g!r}")
        if p.get("gender") not in ("male", "female"):
            errors.append(f"{tag} gender phải là male/female: {p.get('gender')!r}")
        gender.setdefault(name, set()).add(p.get("gender"))
    if persons and not any(isinstance(p, dict) and p.get("generation") == 1 for p in persons):
        errors.append("không có người nào ở generation 1 (cụ tổ)")

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
            errors.append(f"'{fa}' father của '{child}' nhưng thiếu '{wife}' (vợ duy nhất) mother của '{child}'")
        for t, p in par.items():
            inv = "son" if "male" in gset(child) else "daughter"
            if (child, p, inv) not in rel_set:
                warns.append(f"thiếu quan hệ ngược '{child}' -> '{p}' ({inv})")

    n_sent = len([s for s in re.split(r"[.!?]\s+|[.!?]$", inp) if s.strip()])
    if not 3 <= n_sent <= 6:
        warns.append(f"Input có {n_sent} câu (yêu cầu 3-6)")
    return errors, warns


def validate_file(path):
    ok, bad, inputs = 0, 0, []
    print(f"\n=== {path} ===")
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
                    if set(rec) != {"text"}:
                        warns.append(f"có field thừa ngoài 'text': {sorted(set(rec) - {'text'})}")
                    try:
                        _, inp, resp = split_text(rec["text"])
                        try:
                            ans = json.loads(resp)
                            e2, w2 = check_answer(ans, inp)
                            errors += e2
                            warns += w2
                        except json.JSONDecodeError as e:
                            errors.append(f"Response không phải JSON hợp lệ: {e}")
                    except ValueError as e:
                        errors.append(str(e))
            for w in warns:
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
    print(f"--> hợp lệ: {ok} | lỗi: {bad} | tổng: {ok + bad}")
    return ok, bad, inputs


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("files", nargs="*", type=Path, default=DEFAULT_FILES)
    args = ap.parse_args()
    total_bad, all_inputs = 0, {}
    for f in args.files:
        _, bad, inputs = validate_file(f)
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
