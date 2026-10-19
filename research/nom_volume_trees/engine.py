"""Bộ máy gán nhãn dùng chung: dò offset tuần tự trong hannom_text, kiểm tra, ghi pages/NNN.json."""
import json, os

def run(pages, src_dir, out_dir, doc_id, note):
    os.makedirs(os.path.join(out_dir, "pages"), exist_ok=True)
    stats = {"entities": 0, "relations": 0, "by_label": {}, "by_rel": {}, "pages": 0}
    errors = []
    for n in sorted(pages):
        spec = pages[n]
        src = json.load(open(os.path.join(src_dir, f"{n:03d}.json"), encoding="utf-8"))
        text = src["hannom_text"]
        ents, keyidx, used, pos = [], {}, [], 0
        for key, label, s in spec.get("ents", []):
            if key in keyidx:
                errors.append(f"trang {n}: key trùng {key}"); continue
            i = text.find(s, pos)
            if i < 0:
                errors.append(f"trang {n}: không tìm thấy {key} {s!r} sau vị trí {pos}"); continue
            if any(a < i + len(s) and i < b for a, b in used):
                errors.append(f"trang {n}: chồng lấn {key} {s!r}"); continue
            used.append((i, i + len(s)))
            assert text[i:i + len(s)] == s
            keyidx[key] = len(ents)
            ents.append({"start": i, "end": i + len(s), "label": label, "text": s})
            pos = i + len(s)
            stats["by_label"][label] = stats["by_label"].get(label, 0) + 1
        rels = []
        for typ, h, t, conf, cue in spec.get("rels", []):
            if h not in keyidx or t not in keyidx:
                errors.append(f"trang {n}: quan hệ thiếu thực thể {h}->{t}"); continue
            if ents[keyidx[h]]["label"] != "PER_NAME" or ents[keyidx[t]]["label"] != "PER_NAME":
                errors.append(f"trang {n}: quan hệ không phải PER_NAME {h}->{t}"); continue
            rels.append({"type": typ, "head": keyidx[h], "tail": keyidx[t], "confidence": conf, "evidence": cue})
            stats["by_rel"][typ] = stats["by_rel"].get(typ, 0) + 1
        stats["entities"] += len(ents); stats["relations"] += len(rels); stats["pages"] += 1
        out = {
            "doc_id": doc_id, "lang": "han", "page_number": n,
            "provenance": {"book_id": doc_id, "scan_id": src["scan_id"], "page_id": f"{n:03d}", "ocr_source": note},
            "source": "silver_claude",
            "hannom_text": text, "transliteration_text": src["transliteration_text"], "translation_text": src["translation_text"],
            "entities": ents, "relations": rels,
        }
        with open(os.path.join(out_dir, "pages", f"{n:03d}.json"), "w", encoding="utf-8") as fh:
            json.dump(out, fh, ensure_ascii=False, indent=2)
    return stats, errors
