"""Auto-label Phả ký (pha_he diagram + regex, no Gemini) then have Gemini review the labels.

Bước 1 — nhãn tự động: ``build_gold_extraction(text, pha_he, {})`` (giống ``generate_prelabel``),
không có Gemini, nên bước rà soát của Gemini là một lượt kiểm tra độc lập với nguồn nhãn.

Bước 2 — Gemini rà: văn bản được cắt theo dòng (``chunk_spans``); mỗi đoạn gửi kèm nhãn tự động
nằm trong đoạn. Gemini trả lại **danh sách đã sửa đầy đủ**; script tự so với nhãn tự động để ghi
nguồn gốc từng nhãn (kept / removed / added). Entity không xuất hiện nguyên văn trong đoạn bị loại.
Quan hệ tự động có head/tail ở hai đoạn khác nhau không được rà — giữ nguyên, đánh dấu riêng.
Mỗi lần gửi dùng một chat mới. Khi tool đọc trượt (rỗng / câu chào / JSON dở) dù Gemini đã trả lời,
script tìm câu trả lời trong trang theo nội dung (khối chứa ``"entities"`` + ``"relations"``, không
phải prompt) trước khi tính là lỗi. Đoạn lỗi được thử lại ``--retries`` lần; mỗi lần lỗi chụp màn
hình ``chunkNN_attemptK_failed.png`` để chẩn đoán.

Backend:
- ``dry-run`` (mặc định): chỉ ghi prompt + đếm ký tự, không gọi dịch vụ nào.
- ``tool``: ``ToolGeminiAPI`` (Selenium điều khiển gemini.google.com) trong
  ``research/hannom-bilingual-dataset/TOOL_Gemini_API``. Script dùng bản sao ``.ini`` của tool với
  ``context_content`` rỗng để không gửi prompt dịch cn/sv/vi lúc khởi tạo.

Đầu ra ``<output>/<tree_id>/``: ``auto.entities.json``, ``review.chunks.jsonl`` (prompt, câu trả lời
thô, diff), ``reviewed.entities.json`` và ``gold.training.json`` (cùng định dạng gold, nên
``build_llm_sft_dataset --gold-dir <output>`` đọc được trực tiếp).
"""

from __future__ import annotations

import argparse
import configparser
import json
import logging
import re
import sys
import time
import unicodedata
from collections import Counter
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

from label_studio_pipeline.build_llm_sft_dataset import chunk_spans
from label_studio_pipeline.corpus_store import load_json, tree_dir
from label_studio_pipeline.data_layout import DATA_ROOT, GOLD_LABELS, RAW_VGP_CORPUS, REPO_ROOT
from label_studio_pipeline.gemini_extractor import GeminiExtractionError, normalize_extraction
from label_studio_pipeline.gold_builder import build_gold_extraction, to_training_record

DEFAULT_OUTPUT = DATA_ROOT / "01_interim" / "gemini_review" / "v2"
DEFAULT_TOOL_DIR = REPO_ROOT / "research" / "hannom-bilingual-dataset" / "TOOL_Gemini_API"
DEFAULT_MAX_CHARS = 3000
DEFAULT_TOOL_TIMEOUT = 300
REVIEW_VERSION = "gemini-review-v2"
DEFAULT_RETRIES = 1
DEFAULT_STABLE_POLLS = 6
DEFAULT_DOM_WAIT = 90
PROMPT_MARKER = "NHÃN TỰ ĐỘNG"
MAX_BROWSER_RESTARTS = 3

REVIEW_PROMPT = """\
Bạn là người rà soát nhãn trích xuất thông tin gia phả tiếng Việt.
Dưới đây là MỘT ĐOẠN Phả ký và NHÃN TỰ ĐỘNG (do máy gán, có thể sai hoặc thiếu).
Hãy kiểm tra từng nhãn so với đoạn văn rồi trả về DANH SÁCH NHÃN ĐÃ SỬA ĐẦY ĐỦ:
giữ nhãn đúng, bỏ nhãn sai, sửa nhãn sai loại, thêm nhãn còn thiếu.

Quy tắc:
- entities: {{"text": ..., "label": ...}}. "text" phải chép NGUYÊN VĂN từ đoạn (đúng hoa/thường, dấu),
  nằm trên MỘT dòng (không chứa ký tự xuống dòng). Mỗi chuỗi chỉ một nhãn, không chồng lấn.
  label ∈ PER_NAME, LOC, DATE (thời điểm, năm), GENERATION (đời thứ…), ORDER (con trưởng, con thứ…).
- PER_NAME: chỉ phần tên người (họ tên, hoặc tên húy / tên tự / tên hiệu). KHÔNG gộp danh xưng
  (ông, bà, cụ, cụ ông, cụ bà, ngài, Thuỷ Tổ, Tổ, Tỷ) và KHÔNG gộp chữ đánh dấu "húy/huý", "tự",
  "hiệu" vào span. Ví dụ "Thuỷ Tổ Đinh Công Huý Tư Đức Tuyên" → "Đinh Công", "Tư Đức Tuyên".
- LOC: mỗi địa danh một span riêng. Ví dụ "Đông hưng - Thái Bình" → "Đông hưng", "Thái Bình";
  "Dòng họ Vũ An Bài" → LOC chỉ là "An Bài" (chữ "Vũ" là họ, không phải địa danh).
- relations: {{"type": ..., "head": ..., "tail": ...}} giữa hai PER_NAME có trong entities.
  FATHER_OF: head là cha, tail là con. MOTHER_OF: head là mẹ, tail là con. SPOUSE: vợ chồng.
- Chỉ ghi quan hệ được văn bản nói rõ hoặc suy ra trực tiếp trong đoạn này; không đoán.
- Không thêm người không xuất hiện trong đoạn.
- Chỉ trả về MỘT object JSON {{"entities": [...], "relations": [...]}}, không markdown, không giải thích.

ĐOẠN VĂN:
<<<
{text}
>>>

NHÃN TỰ ĐỘNG:
{labels}
"""

JSON_OBJECT = re.compile(r"\{.*\}", re.DOTALL)
ANSWER_START = re.compile(r'\{\s*"entities"')

logger = logging.getLogger(__name__)


@dataclass
class ReviewBackend:
    review: Callable[[str], str | None]
    new_chat: Callable[[], None]
    screenshot: Callable[[Path], bool]
    close: Callable[[], None]
    # Text các khối trong trang chứa đủ các marker (tìm câu trả lời theo nội dung, không theo selector).
    dom_texts: Callable[..., list[str]] | None = None


def _configure_logging(verbose: bool) -> None:
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )


def _key(text: str) -> str:
    return " ".join(text.split()).casefold()


def labels_for_chunk(chunk_text: str, auto: dict) -> tuple[list[dict], list[dict]]:
    """Auto entities whose text occurs in the chunk, and relations with both ends among them."""
    entities = [e for e in auto["entities"] if e["text"] in chunk_text]
    names = {e["text"] for e in entities if e["label"] == "PER_NAME"}
    relations = [
        {"type": r["type"], "head": r["head"], "tail": r["tail"]}
        for r in auto["relations"]
        if r["head"] in names and r["tail"] in names
    ]
    return entities, relations


def labels_json(entities: list[dict], relations: list[dict]) -> str:
    return json.dumps(
        {"entities": [{"text": e["text"], "label": e["label"]} for e in entities], "relations": relations},
        ensure_ascii=False,
    )


def build_prompt(chunk_text: str, entities: list[dict], relations: list[dict]) -> str:
    return REVIEW_PROMPT.format(text=chunk_text, labels=labels_json(entities, relations))


def _json_key(text: str) -> str | None:
    match = JSON_OBJECT.search(text or "")
    if match is None:
        return None
    try:
        return json.dumps(json.loads(match.group(0)), sort_keys=True, ensure_ascii=False)
    except json.JSONDecodeError:
        return None


def _squash(text: str) -> str:
    return " ".join(unicodedata.normalize("NFC", text or "").split())


def find_answer_in_dom(
    backend: "ReviewBackend",
    prompt: str,
    prompt_labels: str,
    chunk_text: str,
    counters: Counter,
    max_wait: float,
    poll: float = 2.0,
) -> tuple[dict | None, str | None]:
    """Tìm câu trả lời JSON trong trang theo nội dung, chờ đến khi text đứng yên.

    Loại khối chứa prompt (marker "NHÃN TỰ ĐỘNG"), khối là một phần của prompt (vd dòng quy tắc
    ``{"entities": [...], "relations": [...]}``) và khối trùng y nhãn tự động đã gửi, để không
    nhận nhầm chính prompt của mình là câu trả lời. Mỗi đoạn chạy trong chat mới nên trang chỉ có
    đúng một câu trả lời của đoạn này.
    """
    labels_key = _json_key(prompt_labels)
    prompt_squashed = _squash(prompt)
    deadline = time.monotonic() + max_wait
    last = None
    while True:
        texts = backend.dom_texts('"entities"', '"relations"') if backend.dom_texts else []
        candidates = [
            t
            for t in texts
            if PROMPT_MARKER not in t and _squash(t) not in prompt_squashed and _json_key(t) != labels_key
        ]
        if candidates:
            text = candidates[-1]
            if text == last:
                try:
                    return parse_review(text, chunk_text, counters), text
                except GeminiExtractionError:
                    pass  # còn đang viết / chưa phải JSON hoàn chỉnh → chờ tiếp
            last = text
        if time.monotonic() >= deadline:
            return None, last
        time.sleep(poll)


def _occurrences(text: str, needle: str) -> list[tuple[int, int]]:
    spans, pos = [], text.find(needle)
    while pos != -1:
        spans.append((pos, pos + len(needle)))
        pos = text.find(needle, pos + 1)
    return spans


def drop_nested_entities(entities: list[dict], chunk_text: str, counters: Counter) -> list[dict]:
    """Bỏ entity mà MỌI lần xuất hiện đều nằm trong một entity dài hơn (quy tắc không chồng lấn).

    Vd "Việt Nam" chỉ xuất hiện bên trong "Việt Nam Quốc" → bỏ; nếu còn đứng riêng ở chỗ khác → giữ.
    """
    longer_spans: dict[str, list[tuple[int, int]]] = {e["text"]: _occurrences(chunk_text, e["text"]) for e in entities}
    kept = []
    for ent in entities:
        own = longer_spans[ent["text"]]
        containers = [
            span
            for other, spans in longer_spans.items()
            if len(other) > len(ent["text"]) and ent["text"] in other
            for span in spans
        ]
        if own and containers and all(any(c0 <= s0 and s1 <= c1 for c0, c1 in containers) for s0, s1 in own):
            counters["gemini_entity_nested_dropped"] += 1
            continue
        kept.append(ent)
    return kept


def load_answer_json(raw: str, counters: Counter) -> dict:
    """Lấy object JSON câu trả lời.

    Gemini đôi khi viết dở rồi viết lại từ đầu ngay trong cùng câu trả lời
    (vd ``…"tail": "Ngô{"entities": [...]}``, thấy trên ảnh chụp 03.10.2026) → thử từ lần
    ``{"entities"`` CUỐI CÙNG trở về trước, lấy object đầu tiên decode được trọn vẹn.
    """
    raw = raw or ""
    decoder = json.JSONDecoder()
    starts = [m.start() for m in ANSWER_START.finditer(raw)]
    for n, start in enumerate(reversed(starts)):
        try:
            payload, _ = decoder.raw_decode(raw, start)
        except json.JSONDecodeError:
            continue
        if isinstance(payload, dict):
            if n or len(starts) > 1:
                counters["gemini_json_restart_recovered"] += 1
            return payload
    match = JSON_OBJECT.search(raw)
    if match is None:
        raise GeminiExtractionError("no JSON object in response")
    try:
        payload = json.loads(match.group(0))
    except json.JSONDecodeError as exc:
        raise GeminiExtractionError(f"invalid JSON: {exc}") from exc
    if not isinstance(payload, dict):
        raise GeminiExtractionError("response JSON is not an object")
    return payload


def parse_review(raw: str, chunk_text: str, counters: Counter) -> dict:
    """Parse Gemini's corrected list; drop entities not verbatim in chunk and dangling relations."""
    extraction = normalize_extraction(load_answer_json(raw, counters))
    # Văn bản đã chuẩn hoá NFC (review_tree); Gemini cũng trả NFC nhưng chuẩn hoá lại cho chắc.
    for ent in extraction["entities"]:
        ent["text"] = unicodedata.normalize("NFC", ent["text"])
    for rel in extraction["relations"]:
        rel["head"] = unicodedata.normalize("NFC", rel["head"])
        rel["tail"] = unicodedata.normalize("NFC", rel["tail"])

    entities = []
    for ent in extraction["entities"]:
        if "\n" in ent["text"]:
            counters["gemini_entity_multiline"] += 1
        elif ent["text"] in chunk_text:
            entities.append(ent)
        else:
            counters["gemini_entity_not_in_text"] += 1
    entities = drop_nested_entities(entities, chunk_text, counters)
    names = {e["text"] for e in entities if e["label"] == "PER_NAME"}
    relations = []
    for rel in extraction["relations"]:
        if rel["head"] in names and rel["tail"] in names and rel["head"] != rel["tail"]:
            relations.append({"type": rel["type"], "head": rel["head"], "tail": rel["tail"]})
        else:
            counters["gemini_relation_dangling"] += 1
    return {"entities": entities, "relations": relations}


def diff_labels(before: dict, after: dict) -> dict:
    ent_b = {(_key(e["text"]), e["label"]) for e in before["entities"]}
    ent_a = {(_key(e["text"]), e["label"]) for e in after["entities"]}
    rel_b = {(r["type"], _key(r["head"]), _key(r["tail"])) for r in before["relations"]}
    rel_a = {(r["type"], _key(r["head"]), _key(r["tail"])) for r in after["relations"]}
    return {
        "entities_kept": len(ent_b & ent_a),
        "entities_removed": sorted(ent_b - ent_a),
        "entities_added": sorted(ent_a - ent_b),
        "relations_kept": len(rel_b & rel_a),
        "relations_removed": sorted(rel_b - rel_a),
        "relations_added": sorted(rel_a - rel_b),
    }


def _merge(groups: list[dict]) -> dict:
    entities: list[dict] = []
    relations: list[dict] = []
    seen_e: set[tuple[str, str]] = set()
    seen_r: set[tuple[str, str, str]] = set()
    for group in groups:
        for ent in group["entities"]:
            k = (_key(ent["text"]), ent["label"])
            if k not in seen_e:
                seen_e.add(k)
                entities.append({"text": ent["text"], "label": ent["label"]})
        for rel in group["relations"]:
            k = (rel["type"], _key(rel["head"]), _key(rel["tail"]))
            if k not in seen_r:
                seen_r.add(k)
                relations.append(
                    {
                        "type": rel["type"],
                        "head": rel["head"],
                        "tail": rel["tail"],
                        "head_label": "PER_NAME",
                        "tail_label": "PER_NAME",
                    }
                )
    return {"entities": entities, "relations": relations}


def review_tree(
    tree_id: int,
    *,
    corpus_dir: Path,
    out_dir: Path,
    max_chars: int,
    backend: ReviewBackend | None,
    retries: int,
    counters: Counter,
    dom_wait: float = DEFAULT_DOM_WAIT,
    reuse_reviewed: bool = True,
) -> dict:
    base = tree_dir(corpus_dir, tree_id)
    # NFC: vài Phả ký (vd 229, 243) lưu dấu tách rời (NFD) → Gemini trả NFC nên không khớp nguyên văn.
    text = unicodedata.normalize("NFC", (base / "pha_ky.txt").read_text(encoding="utf-8"))
    meta = load_json(base / "meta.json") or {}
    pha_he = load_json(base / "pha_he.json") or {}

    auto, auto_stats = build_gold_extraction(text, pha_he, {"entities": [], "relations": []})
    tree_out = out_dir / str(tree_id)
    tree_out.mkdir(parents=True, exist_ok=True)
    (tree_out / "auto.entities.json").write_text(
        json.dumps({"stats": auto_stats, **auto}, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )

    chunks_path = tree_out / "review.chunks.jsonl"
    # Chạy tiếp: đoạn đã rà xong ở lần trước với ĐÚNG prompt này thì dùng lại, không gửi lại.
    previous: dict[str, dict] = {}
    if backend is not None and reuse_reviewed and chunks_path.is_file():
        for line in chunks_path.read_text(encoding="utf-8").splitlines():
            old = json.loads(line)
            if old.get("status") == "reviewed":
                previous[old["prompt"]] = old

    chunk_rows: list[dict] = []
    reviewed_groups: list[dict] = []
    covered_relations: set[tuple[str, str, str]] = set()
    failed = 0

    def save_progress() -> None:
        # Ghi sau mỗi đoạn (kèm các đoạn cũ chưa tới lượt) để bị ngắt giữa cây lớn không mất phần đã rà.
        done = {row["prompt"] for row in chunk_rows}
        rows = chunk_rows + [old for prompt_key, old in previous.items() if prompt_key not in done]
        with chunks_path.open("w", encoding="utf-8") as fh:
            for row in rows:
                fh.write(json.dumps(row, ensure_ascii=False) + "\n")
    for idx, (start, end) in enumerate(chunk_spans(text, max_chars)):
        chunk_text = text[start:end].strip()
        if not chunk_text:
            continue
        entities, relations = labels_for_chunk(chunk_text, auto)
        covered_relations |= {(r["type"], r["head"], r["tail"]) for r in relations}
        prompt = build_prompt(chunk_text, entities, relations)
        counters["chunks"] += 1
        counters["prompt_chars"] += len(prompt)
        row: dict[str, Any] = {"chunk": idx, "start": start, "end": end, "prompt": prompt}
        before = {"entities": entities, "relations": relations}

        if backend is None:
            row["status"] = "dry_run"
            reviewed_groups.append(before)
            chunk_rows.append(row)
            continue

        old = previous.get(prompt)
        if old is not None:
            counters["chunks_reused"] += 1
            counters["chunks_reviewed"] += 1
            reviewed_groups.append(old["reviewed"])
            chunk_rows.append({**old, "reused": True})
            continue

        attempts: list[dict] = []
        after = None
        prompt_labels = labels_json(entities, relations)
        for attempt in range(1 + retries):
            if attempt:
                counters["chunk_retries"] += 1
            # Mỗi lần gửi một chat mới: prompt tự đủ ngữ cảnh, và trang chỉ còn đúng câu trả lời
            # của lần này (không lẫn câu trả lời của đoạn trước khi tìm theo nội dung).
            backend.new_chat()
            started = time.monotonic()
            raw = backend.review(prompt)
            record: dict[str, Any] = {"seconds": round(time.monotonic() - started, 1), "raw_response": raw}
            try:
                after = parse_review(raw or "", chunk_text, counters)
            except GeminiExtractionError as exc:
                record["error"] = str(exc)
                if backend.dom_texts is not None:
                    # Tool hay đọc trượt (rỗng / câu chào / JSON dở) dù Gemini đã trả lời: tìm lại trong trang.
                    counters["chunk_dom_lookups"] += 1
                    after, dom_text = find_answer_in_dom(backend, prompt, prompt_labels, chunk_text, counters, dom_wait)
                    record["dom_response"] = dom_text
                    record["dom_seconds"] = round(time.monotonic() - started, 1)
                    if after is not None:
                        counters["chunks_recovered_from_dom"] += 1
                        attempts.append(record)
                        break
                shot = tree_out / f"chunk{idx:02d}_attempt{attempt}_failed.png"
                if backend.screenshot(shot):
                    record["screenshot"] = shot.name
                attempts.append(record)
                continue
            attempts.append(record)
            break
        row["attempts"] = attempts

        if after is None:
            # Không nuốt lỗi im lặng: giữ nhãn tự động cho đoạn này và đánh dấu để chạy lại.
            failed += 1
            counters["chunks_failed"] += 1
            row["status"] = "failed"
            reviewed_groups.append(before)
        else:
            counters["chunks_reviewed"] += 1
            if len(attempts) > 1:
                counters["chunks_recovered_by_retry"] += 1
            row["status"] = "reviewed"
            row["reviewed"] = after
            row["diff"] = diff_labels(before, after)
            reviewed_groups.append(after)
        chunk_rows.append(row)
        save_progress()

    # Quan hệ tự động bắc qua hai đoạn: Gemini không thấy, giữ nguyên và đếm riêng.
    cross_chunk = [
        r for r in auto["relations"] if (r["type"], r["head"], r["tail"]) not in covered_relations
    ]
    counters["auto_relations_cross_chunk_unreviewed"] += len(cross_chunk)
    reviewed_groups.append({"entities": [], "relations": cross_chunk})
    reviewed = _merge(reviewed_groups)

    previous = {}  # lượt này đã xử lý mọi đoạn → file chỉ còn đúng các đoạn hiện tại
    save_progress()

    status = "dry_run" if backend is None else ("partial" if failed else "reviewed")
    summary = {
        "tree_id": tree_id,
        "review_version": REVIEW_VERSION,
        "status": status,
        "chunks": len(chunk_rows),
        "chunks_failed": failed,
        "auto_entities": len(auto["entities"]),
        "auto_relations": len(auto["relations"]),
        "reviewed_entities": len(reviewed["entities"]),
        "reviewed_relations": len(reviewed["relations"]),
        "cross_chunk_relations_unreviewed": len(cross_chunk),
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }
    (tree_out / "reviewed.entities.json").write_text(
        json.dumps({"summary": summary, **reviewed}, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    if backend is not None:
        training = to_training_record(
            tree_id=tree_id,
            text=text,
            extraction=reviewed,
            source_url=str(meta.get("pha_ky_url") or ""),
            title=str(meta.get("lineage_name") or meta.get("title") or f"tree_{tree_id}"),
        )
        training["source"] = f"{REVIEW_VERSION}:{status}"
        (tree_out / "gold.training.json").write_text(
            json.dumps(training, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )
    return summary


def make_tool_backend(tool_dir: Path, out_dir: Path, timeout: int, stable_polls: int) -> ReviewBackend:
    """Start ToolGeminiAPI with a copy of its .ini whose translation context prompt is blanked."""
    config = configparser.ConfigParser(interpolation=None)
    config.read(tool_dir / "tool_gemini_api.ini", encoding="utf-8")
    config.set("context", "context_content", "")
    config.set("context", "timeout", str(timeout))
    config.set("context", "stable_polls", str(stable_polls))
    ini_path = out_dir / "tool_gemini_review.ini"
    with ini_path.open("w", encoding="utf-8") as fh:
        config.write(fh)

    sys.path.insert(0, str(tool_dir))
    from tool_gemini_api import ToolGeminiAPI  # noqa: PLC0415 — chỉ nạp khi dùng backend tool

    tool = ToolGeminiAPI(str(ini_path))

    def screenshot(path: Path) -> bool:
        try:
            return bool(tool.driver.get_screenshot_as_file(str(path)))
        except Exception as exc:  # noqa: BLE001 — chụp màn hình chỉ để chẩn đoán, không được làm hỏng lượt chạy
            logger.warning("screenshot failed: %s", exc)
            return False

    return ReviewBackend(
        review=tool.send_request,
        new_chat=tool.new_chat,
        screenshot=screenshot,
        close=tool.quit,
        dom_texts=tool.texts_containing,
    )


def _is_browser_failure(exc: BaseException) -> bool:
    """Lỗi do Chrome/WebDriver chết (vd InvalidSessionIdException) → cần khởi động lại tool."""
    module = type(exc).__module__
    return module.startswith(("selenium", "urllib3")) or isinstance(exc, ConnectionError)


def _safe_close(backend: ReviewBackend | None) -> None:
    if backend is None:
        return
    try:
        backend.close()
    except Exception as exc:  # noqa: BLE001 — trình duyệt có thể đã chết sẵn
        logger.warning("close backend failed: %s", exc)


def _gold_tree_ids(gold_dir: Path) -> list[int]:
    return sorted(int(p.name) for p in gold_dir.iterdir() if p.is_dir() and p.name.isdigit())


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Auto-label Phả ký and have Gemini review the labels.")
    parser.add_argument("--backend", choices=["dry-run", "tool"], default="dry-run")
    parser.add_argument("--gold-dir", type=Path, default=GOLD_LABELS, help="Lấy danh sách tree_id (139 cây).")
    parser.add_argument("--corpus-dir", type=Path, default=RAW_VGP_CORPUS)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--tree-id", type=int, action="append", dest="tree_ids")
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument("--max-chars", type=int, default=DEFAULT_MAX_CHARS)
    parser.add_argument("--tool-dir", type=Path, default=DEFAULT_TOOL_DIR)
    parser.add_argument("--tool-timeout", type=int, default=DEFAULT_TOOL_TIMEOUT)
    parser.add_argument(
        "--stable-polls",
        type=int,
        default=DEFAULT_STABLE_POLLS,
        help="Số giây câu trả lời phải đứng yên mới coi là xong (tool mặc định 3).",
    )
    parser.add_argument(
        "--dom-wait",
        type=float,
        default=DEFAULT_DOM_WAIT,
        help="Số giây tối đa tìm câu trả lời trong trang khi tool đọc trượt.",
    )
    parser.add_argument("--retries", type=int, default=DEFAULT_RETRIES, help="Số lần thử lại một đoạn lỗi (chat mới).")
    parser.add_argument("--force", action="store_true", help="Rà lại cả cây đã có status=reviewed.")
    parser.add_argument("-v", "--verbose", action="store_true")
    return parser


def main() -> None:
    args = build_parser().parse_args()
    _configure_logging(args.verbose)
    tree_ids = args.tree_ids or _gold_tree_ids(args.gold_dir)
    if args.limit:
        tree_ids = tree_ids[: args.limit]
    args.output.mkdir(parents=True, exist_ok=True)

    def start_backend() -> ReviewBackend:
        return make_tool_backend(args.tool_dir, args.output, args.tool_timeout, args.stable_polls)

    backend = start_backend() if args.backend == "tool" else None
    restarts = 0
    counters: Counter = Counter()
    results: list[dict] = []
    run_path = args.output / f"run_{args.backend}.json"

    def write_run() -> dict:
        # Ghi sau mỗi cây: lượt chạy bị ngắt giữa chừng vẫn còn tổng kết.
        run = {
            "review_version": REVIEW_VERSION,
            "backend": args.backend,
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "max_chars": args.max_chars,
            "retries": args.retries,
            "stable_polls": args.stable_polls,
            "browser_restarts": restarts,
            "counters": dict(counters),
            "trees": results,
        }
        run_path.write_text(json.dumps(run, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        return run

    try:
        for tree_id in tree_ids:
            done = load_json(args.output / str(tree_id) / "reviewed.entities.json") or {}
            if args.backend == "tool" and not args.force and done.get("summary", {}).get("status") == "reviewed":
                counters["trees_skipped_done"] += 1
                continue
            summary = None
            for tree_attempt in range(2):
                try:
                    summary = review_tree(
                        tree_id,
                        corpus_dir=args.corpus_dir,
                        out_dir=args.output,
                        max_chars=args.max_chars,
                        backend=backend,
                        retries=args.retries,
                        counters=counters,
                        dom_wait=args.dom_wait,
                        reuse_reviewed=not args.force,
                    )
                    break
                except FileNotFoundError as exc:
                    logger.error("tree_id=%s: %s", tree_id, exc)
                    counters["trees_missing_corpus"] += 1
                    break
                except Exception as exc:  # noqa: BLE001 — một cây lỗi không được làm dừng cả lượt chạy
                    logger.exception("tree_id=%s failed: %s", tree_id, exc)
                    if backend is None or not _is_browser_failure(exc) or restarts >= MAX_BROWSER_RESTARTS:
                        results.append({"tree_id": tree_id, "status": "error", "error": repr(exc)})
                        counters["trees_error"] += 1
                        break
                    restarts += 1
                    counters["browser_restarts"] += 1
                    logger.warning("Browser died — restarting tool (%d/%d)", restarts, MAX_BROWSER_RESTARTS)
                    _safe_close(backend)
                    backend = start_backend()
                    if tree_attempt == 1:
                        results.append({"tree_id": tree_id, "status": "error", "error": repr(exc)})
                        counters["trees_error"] += 1
            if summary is not None:
                counters[f"trees_{summary['status']}"] += 1
                results.append(summary)
                logger.info("tree_id=%s %s", tree_id, summary)
            write_run()
    finally:
        _safe_close(backend)

    run = write_run()
    json.dump(run["counters"], sys.stdout, ensure_ascii=False, indent=2)
    print()


if __name__ == "__main__":
    main()
