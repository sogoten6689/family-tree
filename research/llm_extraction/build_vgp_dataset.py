"""Dựng bộ train/test thật từ corpus VGP (Phả ký văn xuôi) theo schema persons/relations.

Nguồn (thư mục data/ của repo dữ liệu):
- 03_derived/gia_pha/<tree_id>/pha_ky.txt   văn xuôi -> Input (cắt đoạn)
- 03_derived/gia_pha/<tree_id>/pha_he.json  sơ đồ gốc -> đời, vợ chồng, cha/mẹ - con ("đã đối chiếu")
- 01_interim/gemini_review/v2/<tree_id>/gold.training.json  nhãn silver Gemini (139 cây), dùng bổ sung
  người/quan hệ mà sơ đồ không có; quan hệ Gemini mâu thuẫn với sơ đồ bị bỏ.

Nguyên tắc: chỉ ghi người được nhắc **nguyên văn** trong đoạn; thông tin văn bản và sơ đồ không có
thì để null (birth, death, generation, gender). Không suy đoán.

Chạy:
    python research/llm_extraction/build_vgp_dataset.py                 # tự tìm thư mục data/
    python research/llm_extraction/build_vgp_dataset.py --data-root /path/to/data --out /path/out

Kết quả (mặc định data/03_derived/llm_sft/v3_persons/):
    train.jsonl, test.jsonl      {"text": ..., "meta": {...}}
    review_test.md               bản soát tay tập test (nguồn từng nhãn)
    stats.json                   thống kê, tham số
"""
import argparse
import json
import random
import re
import unicodedata
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path

INSTR = "Trích xuất thực thể và quan hệ gia phả từ văn bản sau. Trả về dạng JSON."
SEED = 42
MAX_CHUNK_CHARS = 1800      # Input tối đa
MAX_RECORD_CHARS = 5000     # cả prompt + đáp án; ~1.700 token, dưới 2048
TEST_RATIO = 0.2
EMPTY_KEEP_RATIO = 0.1      # giữ ~10% đoạn không có người để model học trả rỗng
V2_TEST_TREES = {544, 1454, 1622, 1813, 2346}   # test cũ của llm_sft/v2, luôn để ở test

HONORIFIC = re.compile(r"^(?:(?:ông|bà|cụ|cố|tổ|thủy|thuỷ|thượng|cao|ngài|đức)\s+)+", re.I)
PII = [
    (re.compile(r"[\w.+-]+@[\w-]+(?:\.[\w-]+)+"), "[email]"),
    (re.compile(r"(?:https?://|www\.)\S+"), "[url]"),
    (re.compile(r"(?<!\d)(?:\+?84|0)(?:[\s.-]?\d){8,10}(?!\d)"), "[số điện thoại]"),
]


def nfc(s):
    return unicodedata.normalize("NFC", s)


# ---------------- sơ đồ pha_he ----------------
def clean_name(raw):
    """Trả về (tên, giới tính từ danh xưng) hoặc (None, None) nếu không dùng được."""
    s = nfc(raw)
    s = re.sub(r"\(.*?\)|\(.*$", "", s)
    s = re.sub(r"\s+", " ", s).strip(" .,;:-&()")
    g = None
    low = s.lower()
    if low.startswith("bà "):
        g = "female"
    elif low.startswith("ông ") or low.startswith("cụ ông "):
        g = "male"
    s = HONORIFIC.sub("", s).strip()
    words = s.split()
    if not 2 <= len(words) <= 5 or re.search(r"[\d.…_/\\-]", s) or "..." in raw:
        return None, None
    if " thị " in f" {s.lower()} ":
        g = g or "female"
    return s, g


def parse_pha_he(he):
    """-> persons {pid: {...}}, spouses set((pid,pid)), parent_edges [(parent_pid, child_pid)]"""
    persons, spouse, parent = {}, set(), []
    members = {}
    for n in he["nodes"]:
        parts = [p for p in re.split(r"\+|&", n["name"]) if p.strip()]
        pids = []
        for k, part in enumerate(parts):
            name, g = clean_name(part)
            pid = (n["node_id"], k)
            persons[pid] = {"name": name, "gender": g, "generation": n.get("generation"), "blood": k == 0}
            pids.append(pid)
        # suy giới tính trong một cặp: biết một người -> người kia ngược lại
        if len(pids) == 2:
            a, b = persons[pids[0]], persons[pids[1]]
            if a["gender"] and not b["gender"]:
                b["gender"] = "female" if a["gender"] == "male" else "male"
            elif b["gender"] and not a["gender"]:
                a["gender"] = "female" if b["gender"] == "male" else "male"
        for sp in pids[1:]:
            spouse.add((pids[0], sp))
        members[n["node_id"]] = pids
    for r in he.get("relationships", []):
        if r.get("type") != "parent_of":
            continue
        par, ch = members.get(r["from_id"], []), members.get(r["to_id"], [])
        if not par or not ch:
            continue
        child = ch[0]                       # người huyết thống của nút con
        if len(par) <= 2:                   # >1 vợ: không biết mẹ là ai -> chỉ giữ người huyết thống
            for p in par:
                parent.append((p, child))
        else:
            parent.append((par[0], child))
    return persons, spouse, parent


# ---------------- tiện ích văn bản ----------------
def chunk_text(text, max_chars):
    lines = [l.strip() for l in text.split("\n") if l.strip()]
    pieces = []
    for l in lines:  # dòng quá dài -> cắt theo câu
        if len(l) <= max_chars:
            pieces.append(l)
            continue
        buf = ""
        for s in re.split(r"(?<=[.!?])\s+", l):
            if buf and len(buf) + len(s) + 1 > max_chars:
                pieces.append(buf)
                buf = ""
            buf = (buf + " " + s).strip()
            while len(buf) > max_chars:       # câu không có dấu chấm
                pieces.append(buf[:max_chars])
                buf = buf[max_chars:]
        if buf:
            pieces.append(buf)
    chunks, buf = [], ""
    for p in pieces:
        if buf and len(buf) + len(p) + 1 > max_chars:
            chunks.append(buf)
            buf = ""
        buf = (buf + "\n" + p).strip()
    if buf:
        chunks.append(buf)
    return chunks


def find_mentions(chunk_low, name):
    pat = r"(?<!\w)" + re.escape(name.lower()) + r"(?!\w)"
    return [m.span() for m in re.finditer(pat, chunk_low)]


YEAR = r"(1[0-9]\d\d|20[0-2]\d)"
RE_RANGE = re.compile(r"^\s*[,(]?\s*(?:\(\s*)?" + YEAR + r"\s*[-–—]\s*" + YEAR + r"\s*\)?")
RE_BIRTH = re.compile(r"^[^.;\n]{0,25}?\b(?:sinh|sanh)\s+(?:năm\s+)?" + YEAR, re.I)
RE_DEATH = re.compile(r"^[^.;\n]{0,40}?\b(?:mất|qua đời|tạ thế|từ trần|hy sinh|hi sinh)\s+(?:năm\s+|ngày\s+[\d/ ]+(?:năm\s+)?)?" + YEAR, re.I)


def years_after(chunk, end):
    """Năm sinh/mất ngay sau tên (trong ~60 ký tự, trước dấu chấm). Không chắc -> None."""
    tail = chunk[end:end + 60]
    m = RE_RANGE.match(tail)
    if m:
        b, d = int(m.group(1)), int(m.group(2))
        return (b, d) if b < d else (None, None)
    b = RE_BIRTH.match(tail)
    d = RE_DEATH.match(tail)
    b = int(b.group(1)) if b else None
    d = int(d.group(1)) if d else None
    if b and d and d < b:
        return None, None
    return b, d


def gender_from_context(chunk_low, spans):
    for s, _ in spans:
        before = chunk_low[max(0, s - 12):s]
        if re.search(r"(?:\bbà|\bcụ bà|\bcon gái|\bvợ)\s*$", before):
            return "female"
        if re.search(r"(?:\bông|\bcụ ông|\bcon trai|\bchồng)\s*$", before):
            return "male"
    return None


# ---------------- dựng một đoạn ----------------
def build_chunk(chunk, he_persons, he_spouse, he_parent, gem_names, gem_rels, stat):
    low = chunk.lower()
    # tên sơ đồ -> danh sách pid (một tên có thể trùng nhiều người)
    by_name = defaultdict(list)
    for pid, p in he_persons.items():
        if p["name"]:
            by_name[p["name"].lower()].append(pid)

    found = {}   # key tên lower -> record
    for nlow, pids in by_name.items():
        spans = find_mentions(low, nlow)
        if not spans:
            continue
        s, e = spans[0]
        found[nlow] = {"name": chunk[s:e], "spans": spans, "pids": pids, "src": "pha_he"}
    for g in gem_names:
        glow = nfc(g).lower()
        if glow in found or len(glow.split()) < 2:
            continue
        spans = find_mentions(low, glow)
        if spans:
            s, e = spans[0]
            found[glow] = {"name": chunk[s:e], "spans": spans, "pids": [], "src": "gemini"}
    # bỏ tên nằm gọn trong tên dài hơn ở cùng vị trí (vd "Văn Cải" trong "Đoàn Văn Cải")
    keys = sorted(found, key=len, reverse=True)
    for k in keys:
        for big in keys:
            if big != k and k in big and found.get(big) and found.get(k):
                big_spans = found[big]["spans"]
                if all(any(bs <= s and e <= be for bs, be in big_spans) for s, e in found[k]["spans"]):
                    del found[k]
                    break

    persons, meta_src = [], {}
    pid2name = {}
    for k, f in sorted(found.items(), key=lambda kv: kv[1]["spans"][0][0]):
        unique = len(f["pids"]) == 1
        hp = he_persons[f["pids"][0]] if unique else None
        gen = hp["generation"] if hp else None
        gender = (hp["gender"] if hp else None) or gender_from_context(low, f["spans"])
        if gender is None and " thị " in f" {k} ":
            gender = "female"
        b = d = None
        for s, e in f["spans"]:
            b2, d2 = years_after(chunk, e)
            b, d = b or b2, d or d2
        persons.append({"name": f["name"], "birth": b, "death": d, "generation": gen, "gender": gender})
        meta_src[f["name"]] = f["src"] if unique or f["src"] == "gemini" else "pha_he:trùng_tên"
        if unique:
            pid2name[f["pids"][0]] = f["name"]
        if len(f["pids"]) > 1:
            stat["ten_trung_nhieu_nguoi_trong_so_do"] += 1
    gender_of = {p["name"]: p for p in persons}

    rels, rel_src = [], {}

    def add(a, b, t, src):
        key = (a, b, t)
        if key in rel_src or a == b:
            return
        rels.append({"from": a, "to": b, "type": t})
        rel_src[key] = src

    # 1) quan hệ từ sơ đồ (cả hai người được nhắc trong đoạn)
    he_pairs = set()
    for a, b in he_spouse:
        if a in pid2name and b in pid2name:
            na, nb = pid2name[a], pid2name[b]
            ga = gender_of[na]["gender"]
            h, w = (nb, na) if ga == "female" else (na, nb)
            add(h, w, "spouse", "pha_he")
            he_pairs.add(frozenset((na, nb)))
    for p, c in he_parent:
        if p in pid2name and c in pid2name:
            np_, nc = pid2name[p], pid2name[c]
            gp = gender_of[np_]["gender"]
            he_pairs.add(frozenset((np_, nc)))
            if gp is None:
                stat["bo_quan_he_cha_me_khong_ro_gioi"] += 1
                continue
            add(np_, nc, "father" if gp == "male" else "mother", "pha_he")
    # 2) quan hệ Gemini: giữ nếu không mâu thuẫn với sơ đồ
    in_he = {n for n in gender_of if meta_src[n] == "pha_he"}
    for t, h, tl in gem_rels:
        h, tl = nfc(h), nfc(tl)
        fh = next((p["name"] for p in persons if p["name"].lower() == h.lower()), None)
        ft = next((p["name"] for p in persons if p["name"].lower() == tl.lower()), None)
        if not fh or not ft:
            continue
        if fh in in_he and ft in in_he and frozenset((fh, ft)) not in he_pairs:
            stat["gemini_mau_thuan_so_do_bo"] += 1
            continue
        typ = {"FATHER_OF": "father", "MOTHER_OF": "mother", "SPOUSE": "spouse"}.get(t)
        if not typ:
            continue
        if typ == "father":
            gender_of[fh]["gender"] = gender_of[fh]["gender"] or "male"
        if typ == "mother":
            gender_of[fh]["gender"] = gender_of[fh]["gender"] or "female"
        if typ == "spouse" and gender_of[fh]["gender"] == "female":
            fh, ft = ft, fh
        src = "pha_he+gemini" if (fh, ft, typ) in rel_src else "gemini"
        if (fh, ft, typ) in rel_src:
            rel_src[(fh, ft, typ)] = src
        else:
            add(fh, ft, typ, src)
    # 3) quan hệ ngược con -> cha/mẹ (cần biết giới tính của con)
    for r in list(rels):
        if r["type"] in ("father", "mother"):
            g = gender_of[r["to"]]["gender"]
            if g:
                add(r["to"], r["from"], "son" if g == "male" else "daughter", rel_src[(r["from"], r["to"], r["type"])])
            else:
                stat["thieu_quan_he_nguoc_vi_khong_ro_gioi_con"] += 1
    # sửa giới tính mâu thuẫn với vai (father phải male...)
    for r in rels:
        need = {"father": "male", "son": "male", "mother": "female", "daughter": "female"}.get(r["type"])
        if need and gender_of[r["from"]]["gender"] != need:
            stat["mau_thuan_gioi_tinh"] += 1
            gender_of[r["from"]]["gender"] = need
    return {"persons": persons, "relations": rels}, meta_src, {f"{a}|{b}|{t}": s for (a, b, t), s in rel_src.items()}


def load_gemini(root, tid):
    f = root / "01_interim" / "gemini_review" / "v2" / str(tid) / "gold.training.json"
    if not f.exists():
        return [], []
    g = json.loads(f.read_text(encoding="utf-8"))
    E = g["entities"]
    names = [e["text"] for e in E if e["label"] == "PER_NAME"]
    rels = []
    for r in g.get("relations", []):
        try:
            h, t = E[r["head"]], E[r["tail"]]
        except (IndexError, TypeError):
            continue
        if h["label"] == "PER_NAME" and t["label"] == "PER_NAME":
            rels.append((r["type"], h["text"], t["text"]))
    return names, rels


def scrub(text):
    for pat, rep in PII:
        text = pat.sub(rep, text)
    return text


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--data-root", type=Path)
    ap.add_argument("--out", type=Path)
    args = ap.parse_args()
    from _paths import DATA, VGP_DIR
    root = args.data_root or DATA
    if not (root / "03_derived" / "gia_pha").is_dir():
        raise SystemExit(f"Không thấy {root}/03_derived/gia_pha — truyền --data-root hoặc đặt LLM_DATA_ROOT")
    out = args.out or (VGP_DIR if root == DATA else root / "03_derived" / "llm_sft" / "v3_persons")
    out.mkdir(parents=True, exist_ok=True)
    rng = random.Random(SEED)
    stat = Counter()

    per_tree = {}
    for d in sorted((root / "03_derived" / "gia_pha").iterdir(), key=lambda p: p.name):
        if not (d / "pha_he.json").exists() or not (d / "pha_ky.txt").exists() or not d.name.isdigit():
            continue
        tid = int(d.name)
        text = scrub(nfc((d / "pha_ky.txt").read_text(encoding="utf-8", errors="replace")))
        if not text.strip():
            continue
        persons, spouse, parent = parse_pha_he(json.loads((d / "pha_he.json").read_text(encoding="utf-8")))
        gem_names, gem_rels = load_gemini(root, tid)
        recs = []
        for ci, ch in enumerate(chunk_text(text, MAX_CHUNK_CHARS)):
            ans, psrc, rsrc = build_chunk(ch, persons, spouse, parent, gem_names, gem_rels, stat)
            record = f"### Instruction:\n{INSTR}\n\n### Input:\n{ch}\n\n### Response:\n{json.dumps(ans, ensure_ascii=False)}"
            if len(record) > MAX_RECORD_CHARS:
                stat["bo_doan_qua_dai"] += 1
                continue
            recs.append({"text": record, "meta": {"tree_id": tid, "chunk": ci, "has_gemini": bool(gem_names),
                                                  "person_src": psrc, "relation_src": rsrc}})
        stat["cay"] += 1
        per_tree[tid] = recs

    # chia theo cây: test = test cũ v2 + 20% cây có quan hệ
    rich = sorted(t for t, rs in per_tree.items()
                  if any(json.loads(r["text"].split("### Response:\n")[1])["relations"] for r in rs))
    pool = [t for t in rich if t not in V2_TEST_TREES]
    rng.shuffle(pool)
    test_trees = set(pool[:round(len(rich) * TEST_RATIO)]) | (V2_TEST_TREES & set(per_tree))

    def resp(r):
        return json.loads(r["text"].split("### Response:\n")[1])

    train, test = [], []
    for t, rs in per_tree.items():
        for r in rs:
            a = resp(r)
            if t in test_trees:
                if len(a["persons"]) >= 2 and a["relations"]:   # test: chỉ đoạn có nội dung gia phả
                    test.append(r)
            elif a["persons"] or rng.random() < EMPTY_KEEP_RATIO:
                train.append(r)
    # cùng một đoạn có thể nằm ở 2 cây (gia phả đăng lại) -> bỏ khỏi train để không lộ test
    def inp_of(r):
        return r["text"].split("### Input:\n")[1].split("\n\n### Response:")[0]
    test_inputs = {inp_of(r) for r in test}
    n0 = len(train)
    seen = set()
    train = [r for r in train if inp_of(r) not in test_inputs and not (inp_of(r) in seen or seen.add(inp_of(r)))]
    stat["bo_doan_trung_lap"] = n0 - len(train)
    rng.shuffle(train)
    test.sort(key=lambda r: (r["meta"]["tree_id"], r["meta"]["chunk"]))

    for name, rows in (("train.jsonl", train), ("test.jsonl", test)):
        with open(out / name, "w", encoding="utf-8") as fh:
            for r in rows:
                fh.write(json.dumps(r, ensure_ascii=False) + "\n")

    # bản soát tay
    lines = ["# Soát tay tập test VGP (schema persons/relations)", "",
             "Nguồn nhãn: `pha_he` = khớp sơ đồ gốc · `gemini` = chỉ có trong nhãn silver Gemini, sơ đồ không xác nhận · "
             "`pha_he+gemini` = cả hai. Sửa trực tiếp trong test.jsonl, hoặc ghi chú vào đây.", ""]
    for i, r in enumerate(test, 1):
        a, m = resp(r), r["meta"]
        inp = r["text"].split("### Input:\n")[1].split("\n\n### Response:")[0]
        lines += [f"## {i}. cây {m['tree_id']} – đoạn {m['chunk']}", "", "> " + inp.replace("\n", "\n> "), "",
                  "| Người | Sinh | Mất | Đời | Giới | Nguồn |", "|---|---|---|---|---|---|"]
        for p in a["persons"]:
            lines.append(f"| {p['name']} | {p['birth'] or ''} | {p['death'] or ''} | {p['generation'] or ''} | "
                         f"{p['gender'] or ''} | {m['person_src'].get(p['name'], '')} |")
        lines += ["", "| Từ | Quan hệ | Đến | Nguồn |", "|---|---|---|---|"]
        for x in a["relations"]:
            lines.append(f"| {x['from']} | {x['type']} | {x['to']} | "
                         f"{m['relation_src'].get(x['from'] + '|' + x['to'] + '|' + x['type'], '')} |")
        lines += ["", "- [ ] đã soát", ""]
    (out / "review_test.md").write_text("\n".join(lines), encoding="utf-8")

    def summarize(rows):
        c = Counter()
        for r in rows:
            a = resp(r)
            c["mau"] += 1
            c["nguoi"] += len(a["persons"])
            c["quan_he"] += len(a["relations"])
            c["mau_co_quan_he"] += bool(a["relations"])
            for p in a["persons"]:
                for f in ("birth", "death", "generation", "gender"):
                    c[f"{f}_null"] += p[f] is None
            for s in r["meta"]["relation_src"].values():
                c[f"quan_he_nguon_{s}"] += 1
            for s in r["meta"]["person_src"].values():
                c[f"nguoi_nguon_{s}"] += 1
        return dict(c)

    stats = {"generated_at": datetime.now(timezone.utc).isoformat(),
             "params": {"seed": SEED, "max_chunk_chars": MAX_CHUNK_CHARS, "max_record_chars": MAX_RECORD_CHARS,
                        "test_ratio": TEST_RATIO, "empty_keep_ratio": EMPTY_KEEP_RATIO},
             "test_trees": sorted(test_trees), "train": summarize(train), "test": summarize(test),
             "xu_ly": dict(stat)}
    (out / "stats.json").write_text(json.dumps(stats, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({k: stats[k] for k in ("train", "test", "xu_ly")}, ensure_ascii=False, indent=1))
    print(f"test: {len(test_trees)} cây · ghi vào {out}")


if __name__ == "__main__":
    main()
