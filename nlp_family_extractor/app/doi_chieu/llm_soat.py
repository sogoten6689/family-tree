"""Soát nhãn LLM (schema persons/relations) — đọc các file .jsonl dạng Instruction/Input/Response.

Nguồn: biến LLM_SOAT_DIRS (ngăn bằng ":"); mặc định tìm repo dữ liệu `data/` đi ngược từ file này và
dùng `data/01_interim/llm_synthetic` + `data/03_derived/llm_sft` (quét 2 cấp). File mới tự hiện.
Kết quả soát ghi ở `<file>.reviews.json` cạnh file gốc; file gốc không bị sửa.
Đặt dưới /api/doi-chieu/ để chế độ nghiên cứu (app/research_mode.py) vẫn cho ghi; mọi route đòi admin.
"""

from __future__ import annotations

import hashlib
import json
import os
import unicodedata
from pathlib import Path
from typing import Annotated, Literal

from fastapi import APIRouter, HTTPException, Query, status
from pydantic import BaseModel, Field, StringConstraints

from app.auth.dependencies import AdminUser

M_INSTR, M_INPUT, M_RESP = "### Instruction:\n", "### Input:\n", "### Response:\n"
KEY_RE = r"^[0-9a-f]{16}$"
ID_RE = r"^[0-9a-f]{10}$"


# ---------------- nguồn dữ liệu ----------------
def data_repo() -> Path | None:
    env = os.getenv("LLM_DATA_ROOT")
    if env:
        return Path(env) if Path(env).is_dir() else None
    here = Path(__file__).resolve()
    for p in here.parents:
        if (p / "data" / "03_derived").is_dir():
            return p / "data"
    return None


def roots() -> list[tuple[Path, str]]:
    env = os.getenv("LLM_SOAT_DIRS")
    if env:
        return [(Path(p), "Khác") for p in env.split(":") if p]
    repo = data_repo()
    if repo is None:
        return []
    return [
        (repo / "01_interim" / "llm_synthetic", "Tổng hợp"),
        (repo / "03_derived" / "llm_sft", "VGP (văn xuôi thật)"),
    ]


def _walk(d: Path, depth: int, acc: list[Path]) -> None:
    try:
        entries = sorted(d.iterdir())
    except OSError:
        return
    for e in entries:
        if e.is_dir() and depth > 0 and not e.name.startswith("."):
            _walk(e, depth - 1, acc)
        elif e.is_file() and e.name.endswith(".jsonl") and not e.name.endswith(".reviewed.jsonl"):
            acc.append(e)


def _is_alpaca(p: Path) -> bool:
    try:
        with p.open("rb") as fh:
            head = fh.read(4096).decode("utf-8", errors="ignore")
    except OSError:
        return False
    return head.startswith('{"text"') and "### Instruction" in head


def dataset_id(p: Path) -> str:
    return hashlib.sha1(str(p).encode()).hexdigest()[:10]


def list_files() -> list[dict]:
    out = []
    for root, group in roots():
        files: list[Path] = []
        _walk(root, 2, files)
        for f in files:
            if not _is_alpaca(f):
                continue
            st = f.stat()
            out.append({"id": dataset_id(f), "path": f, "label": str(f.relative_to(root)), "group": group,
                        "mtime": st.st_mtime, "size": st.st_size})
    return out


def find(ds_id: str) -> dict:
    for d in list_files():
        if d["id"] == ds_id:
            return d
    raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Không tìm thấy bộ dữ liệu.")


def review_path(p: Path) -> Path:
    return p.with_name(p.name[: -len(".jsonl")] + ".reviews.json")


# ---------------- đọc mẫu ----------------
def parse_line(line: str, idx: int) -> dict:
    try:
        rec = json.loads(line)
    except json.JSONDecodeError as e:
        return {"idx": idx, "key": f"{idx:016x}", "input": line[:400], "answer": None, "meta": None, "error": f"JSON lỗi: {e}"}
    t = rec.get("text", "")
    i1, i2 = t.find(M_INPUT), t.find(M_RESP)
    inp = t[i1 + len(M_INPUT): i2].strip() if 0 <= i1 < i2 else t
    key = hashlib.sha1(inp.encode()).hexdigest()[:16]
    answer, error = None, None
    try:
        answer = json.loads(t[i2 + len(M_RESP):]) if i2 >= 0 else None
    except json.JSONDecodeError as e:
        error = f"Response lỗi: {e}"
    return {"idx": idx, "key": key, "input": inp, "answer": answer, "meta": rec.get("meta"), "error": error}


_cache: dict[str, tuple[float, int, list[dict]]] = {}


def load_samples(d: dict) -> list[dict]:
    p: Path = d["path"]
    c = _cache.get(str(p))
    if c and c[0] == d["mtime"] and c[1] == d["size"]:
        return c[2]
    lines = [l for l in p.read_text(encoding="utf-8").split("\n") if l.strip()]
    samples = [parse_line(l, i) for i, l in enumerate(lines)]
    _cache[str(p)] = (d["mtime"], d["size"], samples)
    return samples


def load_reviews(p: Path) -> dict:
    try:
        return json.loads(review_path(p).read_text(encoding="utf-8")).get("items", {})
    except (OSError, json.JSONDecodeError):
        return {}


def version() -> str:
    parts = []
    for d in list_files():
        rp = review_path(d["path"])
        r = rp.stat().st_mtime if rp.exists() else 0
        parts.append(f"{d['id']}:{d['mtime']}:{d['size']}:{r}")
    return hashlib.sha1("|".join(parts).encode()).hexdigest()[:12]


def pha_he_lines(tree_id: int, names: list[str]) -> dict | None:
    repo = data_repo()
    if repo is None:
        return None
    f = repo / "03_derived" / "gia_pha" / str(tree_id) / "pha_he.txt"
    if not f.is_file():
        return None
    lines = [l for l in unicodedata.normalize("NFC", f.read_text(encoding="utf-8", errors="replace")).split("\n") if l]
    low = [unicodedata.normalize("NFC", n).lower() for n in names if n.strip()]
    return {"lines": [l for l in lines if any(n in l.lower() for n in low)], "total": len(lines)}


# ---------------- ghi ----------------
def _write_json(p: Path, obj: dict) -> None:
    tmp = p.with_name(p.name + ".tmp")
    tmp.write_text(json.dumps(obj, ensure_ascii=False, indent=1), encoding="utf-8")
    tmp.replace(p)


def save_review(d: dict, key: str, review: dict | None) -> None:
    p: Path = d["path"]
    items = load_reviews(p)
    if review is None:
        items.pop(key, None)
    else:
        items[key] = review
    _write_json(review_path(p), {"version": 1, "dataset": p.name, "items": items})


def export_reviewed(d: dict) -> dict:
    p: Path = d["path"]
    reviews = load_reviews(p)
    out, edited = [], 0
    for i, line in enumerate(l for l in p.read_text(encoding="utf-8").split("\n") if l.strip()):
        s = parse_line(line, i)
        rv = reviews.get(s["key"], {})
        rec = json.loads(line)
        if rv.get("answer"):
            t = rec["text"]
            rec["text"] = t[: t.index(M_RESP) + len(M_RESP)] + json.dumps(rv["answer"], ensure_ascii=False)
            edited += 1
        meta = dict(rec.get("meta") or {})
        meta["review_status"] = rv.get("status", "chua")
        if rv.get("note"):
            meta["review_note"] = rv["note"]
        rec["meta"] = meta
        out.append(json.dumps(rec, ensure_ascii=False))
    target = p.with_name(p.name[: -len(".jsonl")] + ".reviewed.jsonl")
    target.write_text("\n".join(out) + "\n", encoding="utf-8")
    return {"path": str(target), "count": len(out), "edited": edited}


# ---------------- API ----------------
router = APIRouter(prefix="/api/doi-chieu/llm", tags=["Soát nhãn LLM"])

_Name = Annotated[str, StringConstraints(max_length=200)]


class Person(BaseModel):
    name: _Name
    birth: int | None = Field(default=None, ge=0, le=2200)
    death: int | None = Field(default=None, ge=0, le=2200)
    generation: int | None = Field(default=None, ge=0, le=200)
    gender: Literal["male", "female"] | None = None


class Relation(BaseModel):
    from_: _Name = Field(alias="from")
    to: _Name
    type: Literal["spouse", "father", "mother", "son", "daughter"]

    model_config = {"populate_by_name": True}


class Answer(BaseModel):
    persons: list[Person] = Field(max_length=1000)
    relations: list[Relation] = Field(max_length=5000)


class ReviewIn(BaseModel):
    status: Literal["chua", "da", "xem_lai"]
    note: str | None = Field(default=None, max_length=2000)
    answer: Answer | None = None


_Id = Annotated[str, StringConstraints(pattern=ID_RE)]
_Key = Annotated[str, StringConstraints(pattern=KEY_RE)]


@router.get("")
def get_datasets(_: AdminUser) -> dict:
    items = []
    for d in list_files():
        samples = load_samples(d)
        rv = load_reviews(d["path"]).values()
        n_person = sum(len((s["answer"] or {}).get("persons", [])) for s in samples)
        items.append({
            "id": d["id"], "label": d["label"], "group": d["group"], "path": str(d["path"]),
            "mtime": d["mtime"], "mau": len(samples),
            "co_quan_he": sum(1 for s in samples if (s["answer"] or {}).get("relations")),
            "nguoi_tb": round(n_person / len(samples), 1) if samples else 0,
            "da_soat": sum(1 for r in rv if r.get("status") == "da"),
            "xem_lai": sum(1 for r in rv if r.get("status") == "xem_lai"),
            "da_sua": sum(1 for r in rv if r.get("answer")),
        })
    return {"version": version(), "co_du_lieu": bool(roots()), "datasets": items}


@router.get("/phien-ban")
def get_version(_: AdminUser) -> dict:
    return {"version": version()}


@router.get("/{ds_id}")
def get_dataset(ds_id: _Id, _: AdminUser) -> dict:
    d = find(ds_id)
    reviews = load_reviews(d["path"])
    return {
        "id": d["id"], "label": d["label"], "group": d["group"], "path": str(d["path"]),
        "samples": [{**s, "review": reviews.get(s["key"])} for s in load_samples(d)],
    }


@router.get("/{ds_id}/pha-he/{tree_id}")
def get_pha_he(ds_id: _Id, tree_id: int, _: AdminUser, ten: Annotated[list[str], Query(max_length=500)] = []) -> dict:
    find(ds_id)
    res = pha_he_lines(tree_id, ten)
    if res is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Không có sơ đồ gốc của cây này.")
    return res


@router.put("/{ds_id}/soat/{key}")
def put_review(ds_id: _Id, key: _Key, payload: ReviewIn, user: AdminUser) -> dict:
    from datetime import datetime, timezone

    d = find(ds_id)
    if not any(s["key"] == key for s in load_samples(d)):
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Không có mẫu này trong bộ dữ liệu.")
    review = {
        "status": payload.status,
        "note": payload.note or None,
        "answer": payload.answer.model_dump(by_alias=True) if payload.answer else None,
        "updated_at": datetime.now(timezone.utc).isoformat(),
        "by": getattr(user, "email", None),
    }
    try:
        save_review(d, key, review)
    except OSError as e:
        raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Máy chủ không ghi được file soát.") from e
    return {"review": review}


@router.delete("/{ds_id}/soat/{key}")
def delete_review(ds_id: _Id, key: _Key, _: AdminUser) -> dict:
    save_review(find(ds_id), key, None)
    return {"ok": True}


@router.post("/{ds_id}/xuat")
def post_export(ds_id: _Id, _: AdminUser) -> dict:
    return export_reviewed(find(ds_id))
