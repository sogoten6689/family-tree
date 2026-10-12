"""Gán nhãn NER + quan hệ cho văn bản chữ Hán bằng LLM (RamCloud, API kiểu OpenAI) — nhãn MÁY (silver), chưa phải gold.

Đọc `tasks.json` do `build_han_pilot.py` tạo, gọi LLM từng trang, đối chiếu từng thực thể với văn bản bằng CHUỖI (offset LLM
tự tính thường sai nên không dùng), rồi ghi cho mỗi trang:
  gold/<doc_id>.json  — cùng khoá với gold.training.json (text, entities[start,end,label,text], relations[type,head,tail]),
                        offset theo code point (Python), thêm lang="han", source="llm-silver", model_version
  tasks.json          — task Label Studio có `predictions` (offset UTF-16, xem chú thích ở build_han_pilot.codepoint_to_utf16)
  report.json         — số thực thể/quan hệ, thực thể không khớp chuỗi, chi phí token
Chạy lại thì bỏ qua trang đã có. TỐN TIỀN (gọi API). Khoá đọc từ biến môi trường, không ghi vào mã/log.

Quy tắc nhãn theo `docs/schemas/NER_RE_LABEL_SCHEMA_AND_PIPELINE.md` §4 (đề xuất H2–H7, CHƯA được thầy duyệt).

    python -m label_studio_pipeline.han_llm_prelabel --tasks <han_pilot_v1/tasks.json> --out <dir> [--limit N] [--provider gemini|ramcloud|openai]
Khoá: GOOGLE_API_KEY (gemini), RAMCLOUD_KEY (ramcloud), OPENAI_API_KEY (openai).
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import threading
import time
import uuid
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple

from label_studio_pipeline.build_han_pilot import codepoint_to_utf16

# Nhà cung cấp (đều API kiểu OpenAI): base_url, biến môi trường chứa khoá, model mặc định, tham số riêng.
PROVIDERS = {
    "gemini": {"base_url": "https://generativelanguage.googleapis.com/v1beta/openai", "key_env": "GOOGLE_API_KEY", "model": "gemini-flash-latest", "extra": {}},
    "ramcloud": {"base_url": os.getenv("RAMCLOUD_BASE_URL", "https://ramclouds.me/v1"), "key_env": "RAMCLOUD_KEY", "model": "qwen3.8-flash", "extra": {"enable_thinking": False}},
    "openai": {"base_url": "https://api.openai.com/v1", "key_env": "OPENAI_API_KEY", "model": "gpt-4o-mini", "extra": {}},
}
PROVIDER = os.getenv("HAN_PRELABEL_PROVIDER", "gemini")
MODEL = os.getenv("HAN_PRELABEL_MODEL", PROVIDERS[PROVIDER]["model"])
_UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"
LABELS = {"PER_NAME", "GENERATION", "DATE", "ORDER", "LOC"}
REL_TYPES = {"FATHER_OF", "MOTHER_OF", "SPOUSE"}

SYSTEM_PROMPT = """Bạn là chuyên gia gia phả chữ Hán (Hán văn cổ, Việt Nam). Nhận một trang văn bản gia phả chữ Hán do OCR (có thể có chữ sai) và trả về JSON gồm thực thể và quan hệ.

Nhãn thực thể (chép NGUYÊN VĂN chuỗi như trong văn bản, không sửa chữ):
- PER_NAME: tên người, gồm cả hậu tố 公 / 氏 / 君 đi liền tên (ví dụ 清閑公, 陳氏). Không gồm chức tước đứng trước tên.
- GENERATION: đời thứ mấy (ví dụ 第三世, 二世, 始祖).
- DATE: năm / tháng / ngày (cả ngày giỗ, ngày âm lịch), ví dụ 六月初十日, 嘉隆三年.
- ORDER: thứ tự con trong nhánh (ví dụ 長子, 次子, 第三子).
- LOC: địa danh (xã, huyện, tỉnh, làng, xứ đồng, nơi an táng), ví dụ 青池縣姜亭社.

Quan hệ (head/tail là CHUỖI tên người y hệt đã liệt kê ở entities):
- FATHER_OF: head = cha, tail = con. MOTHER_OF: head = mẹ, tail = con. SPOUSE: vợ chồng (配, 娶; ghi một lần).
Chỉ ghi quan hệ văn bản nói rõ hoặc suy chắc chắn theo cách viết gia phả; KHÔNG suy anh/em, ông/cháu. Không chắc thì bỏ.

Trả về DUY NHẤT một JSON, không giải thích:
{"entities":[{"text":"...","label":"PER_NAME"}],"relations":[{"type":"FATHER_OF","head":"...","tail":"..."}]}
Liệt kê thực thể theo thứ tự xuất hiện trong văn bản; mỗi lần xuất hiện ghi một mục. Nếu trang không có gì thì trả {"entities":[],"relations":[]}."""


class _Transient(RuntimeError):
    pass


def _call_once(text: str, model: str, *, provider: str = PROVIDER, transport=None, timeout: float = 120.0) -> Tuple[str, Dict[str, Any]]:
    import httpx

    cfg = PROVIDERS[provider]
    key = os.environ.get(cfg["key_env"], "").strip()
    if not key:
        raise RuntimeError(f"Thiếu biến môi trường {cfg['key_env']}.")
    body = {"model": model, "messages": [{"role": "system", "content": SYSTEM_PROMPT}, {"role": "user", "content": text}], "temperature": 0, **cfg["extra"]}
    with httpx.Client(transport=transport, timeout=timeout) as client:
        response = client.post(f"{cfg['base_url']}/chat/completions", json=body, headers={"Authorization": f"Bearer {key}", "User-Agent": _UA})
    if response.status_code in (429, 500, 502, 503, 504):
        raise _Transient(f"HTTP {response.status_code}: {response.text[:160].replace(key, '***')}")
    if response.status_code >= 400:
        raise RuntimeError(f"HTTP {response.status_code}: {response.text[:200].replace(key, '***')}")
    data = response.json()
    return data["choices"][0]["message"].get("content") or "", data.get("usage", {})


def call_llm(text: str, model: str = MODEL, *, provider: str = PROVIDER, transport=None, retries: int = 6, wait: float = 20.0) -> Tuple[str, Dict[str, Any]]:
    last = ""
    for attempt in range(retries + 1):
        try:
            return _call_once(text, model, provider=provider, transport=transport)
        except _Transient as error:
            last = str(error)
            if attempt < retries:
                time.sleep(wait)
    raise RuntimeError(f"hết lần thử lại: {last}")


def parse_response(raw: str) -> Dict[str, list]:
    """Lấy JSON từ câu trả lời (chịu được rào ```json …``` hoặc chữ thừa); sai định dạng → rỗng."""
    start, end = raw.find("{"), raw.rfind("}")
    if start < 0 or end <= start:
        return {"entities": [], "relations": []}
    try:
        data = json.loads(raw[start : end + 1])
    except json.JSONDecodeError:
        return {"entities": [], "relations": []}
    entities = [
        {"text": e["text"], "label": e["label"]}
        for e in data.get("entities", [])
        if isinstance(e, dict) and isinstance(e.get("text"), str) and e["text"].strip() and e.get("label") in LABELS
    ]
    relations = [
        {"type": r["type"], "head": r["head"], "tail": r["tail"]}
        for r in data.get("relations", [])
        if isinstance(r, dict) and r.get("type") in REL_TYPES and isinstance(r.get("head"), str) and isinstance(r.get("tail"), str)
    ]
    return {"entities": entities, "relations": relations}


def locate_entities(text: str, entities: List[Dict[str, str]]) -> Tuple[List[Dict[str, Any]], int]:
    """Đặt từng thực thể vào văn bản theo thứ tự LLM liệt kê: tìm tiếp từ cuối thực thể trước; không thấy thì tìm
    lại từ đầu một lần xuất hiện chưa dùng. Không khớp chuỗi → bỏ và đếm. Không để hai thực thể chồng nhau."""
    placed: List[Dict[str, Any]] = []
    used: List[Tuple[int, int]] = []
    cursor = 0
    missing = 0

    def overlaps(s: int, e: int) -> bool:
        return any(s < ue and us < e for us, ue in used)

    for ent in entities:
        needle = ent["text"].strip()
        found = -1
        for origin in (cursor, 0):
            pos = text.find(needle, origin)
            while pos >= 0 and overlaps(pos, pos + len(needle)):
                pos = text.find(needle, pos + 1)
            if pos >= 0:
                found = pos
                break
        if found < 0:
            missing += 1
            continue
        used.append((found, found + len(needle)))
        cursor = found + len(needle)
        placed.append({"start": found, "end": found + len(needle), "label": ent["label"], "text": needle})
    placed.sort(key=lambda e: e["start"])
    return placed, missing


def map_relations(entities: List[Dict[str, Any]], relations: List[Dict[str, str]]) -> List[Dict[str, Any]]:
    """Quan hệ theo CHUỖI tên → chỉ số thực thể PER_NAME đầu tiên có chuỗi đó; head=tail hoặc thiếu thì bỏ; bỏ trùng."""
    index: Dict[str, int] = {}
    for i, e in enumerate(entities):
        if e["label"] == "PER_NAME":
            index.setdefault(e["text"], i)
    out, seen = [], set()
    for r in relations:
        h, t = index.get(r["head"].strip()), index.get(r["tail"].strip())
        if h is None or t is None or h == t:
            continue
        key = (r["type"], frozenset((h, t))) if r["type"] == "SPOUSE" else (r["type"], h, t)
        if key not in seen:
            seen.add(key)
            out.append({"type": r["type"], "head": h, "tail": t})
    return out


def label_page(task_data: Dict[str, Any], ask: Callable[[str], Tuple[str, Dict[str, Any]]] = call_llm, model: str = MODEL) -> Dict[str, Any]:
    text = task_data["text"]
    raw, usage = ask(text)
    parsed = parse_response(raw)
    entities, missing = locate_entities(text, parsed["entities"])
    relations = map_relations(entities, parsed["relations"])
    return {
        "doc_id": task_data["doc_id"],
        "lang": "han",
        "text": text,
        "entities": entities,
        "relations": relations,
        "source": "llm-silver",
        "model_version": model,
        "provenance": task_data.get("provenance"),
        "stats": {"llm_entities": len(parsed["entities"]), "unmatched": missing, "llm_relations": len(parsed["relations"]), "usage": usage},
    }


def to_ls_task(doc: Dict[str, Any]) -> Dict[str, Any]:
    text = doc["text"]
    result = []
    for e in doc["entities"]:
        result.append({
            "id": f"ent_{uuid.uuid4().hex[:12]}", "from_name": "label", "to_name": "text", "type": "labels",
            "value": {"start": codepoint_to_utf16(text, e["start"]), "end": codepoint_to_utf16(text, e["end"]),
                      "text": e["text"], "labels": [e["label"]]},
        })
    data = {"text": text, "doc_id": doc["doc_id"], "lang": "han", "provenance": doc.get("provenance")}
    return {"data": data, "predictions": [{"model_version": doc["model_version"], "result": result}]}


def run(tasks_path: Path, out_dir: Path, *, limit: Optional[int] = None, model: str = MODEL, provider: str = PROVIDER, workers: int = 1, ask=None, progress=print) -> Dict[str, Any]:
    ask = ask or (lambda text: call_llm(text, model, provider=provider))
    tasks = json.loads(tasks_path.read_text(encoding="utf-8"))
    if limit:
        tasks = tasks[:limit]
    gold_dir = out_dir / "gold"
    gold_dir.mkdir(parents=True, exist_ok=True)
    docs, errors, tokens = [], 0, {"prompt": 0, "completion": 0}
    lock = threading.Lock()
    done = 0

    def work(task: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        nonlocal errors, done
        data = task["data"]
        path = gold_dir / f"{data['doc_id']}.json"
        if path.exists():
            return json.loads(path.read_text(encoding="utf-8"))
        try:
            doc = label_page(data, ask, model)
        except Exception as error:  # noqa: BLE001 — một trang lỗi không dừng cả lô
            with lock:
                errors += 1
                progress(f"trang {data['doc_id']}: lỗi {str(error)[:140]}")
            return None
        path.write_text(json.dumps(doc, ensure_ascii=False, indent=1), encoding="utf-8")
        usage = doc["stats"]["usage"] or {}
        with lock:
            tokens["prompt"] += usage.get("prompt_tokens", 0)
            tokens["completion"] += usage.get("completion_tokens", 0)
            done += 1
            if done % 25 == 0:
                progress(f"đã gán {done} trang mới ({tokens['prompt'] + tokens['completion']} token)")
        return doc

    with ThreadPoolExecutor(max_workers=max(1, workers)) as pool:
        docs = [d for d in pool.map(work, tasks) if d is not None]
    (out_dir / "tasks.json").write_text(json.dumps([to_ls_task(d) for d in docs], ensure_ascii=False, indent=1), encoding="utf-8")
    labels: Dict[str, int] = {}
    for d in docs:
        for e in d["entities"]:
            labels[e["label"]] = labels.get(e["label"], 0) + 1
    llm_total = sum(d["stats"]["llm_entities"] for d in docs)
    report = {
        "provider": provider,
        "model": model,
        "pages_labeled": len(docs),
        "pages_error": errors,
        "entities": sum(len(d["entities"]) for d in docs),
        "by_label": labels,
        "relations": sum(len(d["relations"]) for d in docs),
        "unmatched_entities": sum(d["stats"]["unmatched"] for d in docs),
        "unmatched_rate": round(sum(d["stats"]["unmatched"] for d in docs) / llm_total, 3) if llm_total else None,
        "tokens_this_run": tokens,
        "note": "Nhãn máy (silver), chưa phải gold; quy tắc nhãn Hán D3–D7 chưa được thầy duyệt.",
    }
    (out_dir / "report.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    return report


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--tasks", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--limit", type=int)
    parser.add_argument("--workers", type=int, default=1, help="số luồng gọi song song (mặc định 1)")
    parser.add_argument("--provider", choices=sorted(PROVIDERS), default=PROVIDER)
    parser.add_argument("--model", help="mặc định theo nhà cung cấp")
    args = parser.parse_args(argv)
    model = args.model or PROVIDERS[args.provider]["model"]
    print(json.dumps(run(args.tasks, args.out, limit=args.limit, model=model, provider=args.provider, workers=args.workers), ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
