#!/usr/bin/env python3
"""OCR local page images with PP-OCRv6 (runs on this machine, no Kim Hán Nôm API).

Does not overwrite existing *-ocr-raw.json / *-boundingbox.json.
Writes a paddleocr/ folder so you can A/B against the lab engine.

Examples (from repo root, paddle venv active):

  python nlp_family_extractor/tools/ocr_paddleocr.py --help

  python nlp_family_extractor/tools/ocr_paddleocr.py \\
    --input data/du_lieu_han_nom_moi/gia_pha_chi \\
    --pages 11-16
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Sequence

IMAGE_SUFFIXES = {".jpg", ".jpeg", ".png", ".tif", ".tiff", ".bmp", ".webp"}
PAGE_RANGE_RE = re.compile(r"^(\d+)\s*-\s*(\d+)$")


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def parse_pages(spec: str | None) -> set[int] | None:
    if not spec:
        return None
    pages: set[int] = set()
    for chunk in spec.split(","):
        token = chunk.strip()
        if not token:
            continue
        ranged = PAGE_RANGE_RE.match(token)
        if ranged:
            start, end = int(ranged.group(1)), int(ranged.group(2))
            if end < start:
                start, end = end, start
            pages.update(range(start, end + 1))
            continue
        pages.add(int(token))
    return pages


def list_page_images(input_dir: Path, pages: set[int] | None) -> list[Path]:
    folders = [input_dir]
    nested = input_dir / "pages"
    if nested.is_dir():
        folders.append(nested)
    images: list[Path] = []
    seen: set[Path] = set()
    for folder in folders:
        if not folder.is_dir():
            continue
        for path in folder.iterdir():
            if not path.is_file() or path.suffix.lower() not in IMAGE_SUFFIXES:
                continue
            if not re.fullmatch(r"\d+", path.stem):
                continue
            resolved = path.resolve()
            if resolved in seen:
                continue
            seen.add(resolved)
            images.append(path)
    images.sort(key=lambda path: int(path.stem))
    if pages is not None:
        images = [path for path in images if int(path.stem) in pages]
    return images


def _to_list(value: Any) -> Any:
    if value is None:
        return None
    if hasattr(value, "tolist"):
        return value.tolist()
    if isinstance(value, (list, tuple)):
        return [_to_list(item) for item in value]
    return value


def _result_mapping(res: Any) -> dict[str, Any]:
    if isinstance(res, dict):
        return res
    json_attr = getattr(res, "json", None)
    if isinstance(json_attr, dict):
        return json_attr
    if callable(json_attr):
        maybe = json_attr()
        if isinstance(maybe, dict):
            return maybe
    keys_fn = getattr(res, "keys", None)
    if callable(keys_fn):
        try:
            return {key: res[key] for key in keys_fn()}
        except Exception:
            pass
    raise TypeError(f"Unrecognized PaddleOCR result type: {type(res)!r}")


def _lines_from_mapping(mapping: dict[str, Any]) -> list[dict[str, Any]]:
    texts = mapping.get("rec_texts") or []
    scores = mapping.get("rec_scores") or []
    polys = mapping.get("rec_polys") or mapping.get("dt_polys") or []
    lines: list[dict[str, Any]] = []
    for index, text in enumerate(texts):
        score = float(scores[index]) if index < len(scores) else None
        poly = _to_list(polys[index]) if index < len(polys) else None
        lines.append({"text": str(text), "score": score, "poly": poly})
    return lines


def build_page_record(
    *,
    source: Path,
    model: str,
    elapsed_s: float,
    mapping: dict[str, Any],
    lines: list[dict[str, Any]],
) -> dict[str, Any]:
    texts = [line["text"] for line in lines]
    bbox = []
    for line in lines:
        poly = line["poly"] or []
        bbox.append([poly, [line["text"], line["score"]]])
    return {
        "engine": "paddleocr",
        "model": model,
        "source": source.name,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "elapsed_s": round(elapsed_s, 3),
        "result_ocr_text": texts,
        "result_bbox": bbox,
        "line_count": len(texts),
        "mean_score": (
            round(sum(line["score"] for line in lines if line["score"] is not None) / len(lines), 4)
            if lines
            else None
        ),
        "paddle_keys": sorted(str(key) for key in mapping.keys()),
    }


def configure_cache() -> Path:
    cache_dir = _repo_root() / ".paddlex-cache"
    cache_dir.mkdir(parents=True, exist_ok=True)
    os.environ.setdefault("PADDLE_PDX_CACHE_HOME", str(cache_dir))
    return cache_dir


def make_ocr(model: str, engine: str | None) -> Any:
    from paddleocr import PaddleOCR

    rec_name = f"PP-OCRv6_{model}_rec"
    det_name = f"PP-OCRv6_{model}_det"
    kwargs: dict[str, Any] = dict(
        text_detection_model_name=det_name,
        text_recognition_model_name=rec_name,
        use_doc_orientation_classify=False,
        use_doc_unwarping=False,
        use_textline_orientation=True,
    )
    if engine:
        kwargs["engine"] = engine
    return PaddleOCR(**kwargs)


def load_ocr(model: str, engine: str) -> tuple[Any, str]:
    """Return (pipeline, resolved_engine). Mac + Paddle 3.0 cannot load v6 static graphs."""
    configure_cache()
    try:
        import paddleocr  # noqa: F401
    except ImportError as exc:
        raise SystemExit(
            "Chưa cài PaddleOCR. Từ thư mục repo:\n"
            "  ~/.pyenv/versions/3.11.9/bin/python -m venv .venv-paddleocr\n"
            "  .venv-paddleocr/bin/pip install -U pip\n"
            "  .venv-paddleocr/bin/pip install -r nlp_family_extractor/requirements-paddleocr.txt\n"
        ) from exc

    requested = None if engine == "auto" else engine
    try:
        ocr = make_ocr(model, requested)
        return ocr, requested or "paddle"
    except ValueError as exc:
        if engine == "auto" and "strides" in str(exc):
            print(
                "PaddlePaddle 3.0 trên macOS không load được graph PP-OCRv6 (lỗi strides).\n"
                "Chuyển sang engine onnxruntime."
            )
            ocr = make_ocr(model, "onnxruntime")
            return ocr, "onnxruntime"
        raise


def ocr_one(ocr: Any, image: Path) -> tuple[dict[str, Any], float, Any]:
    started = time.perf_counter()
    raw = ocr.predict(str(image))
    elapsed = time.perf_counter() - started
    if isinstance(raw, list):
        if not raw:
            raise RuntimeError(f"PaddleOCR returned empty result for {image.name}")
        first = raw[0]
    else:
        first = raw
    mapping = _result_mapping(first)
    return mapping, elapsed, first


def write_outputs(
    *,
    output_dir: Path,
    image: Path,
    record: dict[str, Any],
    paddle_result: Any,
    save_preview: bool,
) -> dict[str, Path]:
    output_dir.mkdir(parents=True, exist_ok=True)
    stem = image.stem
    json_path = output_dir / f"{stem}-paddleocr.json"
    txt_path = output_dir / f"{stem}-paddleocr.txt"
    json_path.write_text(json.dumps(record, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    txt_path.write_text("\n".join(record["result_ocr_text"]) + ("\n" if record["result_ocr_text"] else ""), encoding="utf-8")
    written = {"json": json_path, "txt": txt_path}
    if save_preview and hasattr(paddle_result, "save_to_img"):
        preview_dir = output_dir / "preview"
        preview_dir.mkdir(parents=True, exist_ok=True)
        paddle_result.save_to_img(str(preview_dir))
        written["preview_dir"] = preview_dir
    return written


def existing_lab_texts(image: Path) -> list[str]:
    raw_path = image.with_name(f"{image.stem}-ocr-raw.json")
    box_path = image.with_name(f"{image.stem}-boundingbox.json")
    for path in (box_path, raw_path):
        if not path.exists():
            continue
        payload = json.loads(path.read_text(encoding="utf-8"))
        texts = payload.get("result_ocr_text")
        if isinstance(texts, list):
            return [str(item) for item in texts]
    return []


def print_compare(image: Path, paddle_texts: Sequence[str]) -> None:
    lab = existing_lab_texts(image)
    print(f"  so sánh với Kim Hán Nôm: lab {len(lab)} dòng / paddle {len(paddle_texts)} dòng")
    if not lab:
        print("  (chưa có file *-ocr-raw.json / *-boundingbox.json)")
        return
    show = min(3, max(len(lab), len(paddle_texts)))
    for index in range(show):
        left = lab[index] if index < len(lab) else "—"
        right = paddle_texts[index] if index < len(paddle_texts) else "—"
        print(f"    lab[{index}]: {left}")
        print(f"    pad[{index}]: {right}")


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="OCR ảnh trang gia phả bằng PP-OCRv6 (local)."
    )
    parser.add_argument(
        "--input",
        type=Path,
        default=_repo_root() / "data/du_lieu_han_nom_moi/gia_pha_chi",
        help="Thư mục chứa 0.jpg, 1.jpg, …",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=None,
        help="Mặc định: <input>/paddleocr/",
    )
    parser.add_argument(
        "--pages",
        default=None,
        help="Ví dụ: 11 hoặc 11-16 hoặc 1,11,16. Mặc định: mọi trang số.",
    )
    parser.add_argument(
        "--model",
        choices=("tiny", "small", "medium"),
        default="medium",
        help="PP-OCRv6 size. medium = chất lượng tốt nhất.",
    )
    parser.add_argument(
        "--engine",
        choices=("auto", "paddle", "onnxruntime", "transformers", "paddle_dynamic"),
        default="auto",
        help="auto: paddle, nếu lỗi graph v6 thì onnxruntime (cần trên Mac Intel).",
    )
    parser.add_argument(
        "--skip-existing",
        action="store_true",
        help="Bỏ qua trang đã có *-paddleocr.json.",
    )
    parser.add_argument(
        "--no-preview",
        action="store_true",
        help="Không ghi overlay bbox.",
    )
    parser.add_argument(
        "--compare",
        action="store_true",
        default=True,
        help="In vài dòng so với OCR lab (mặc định bật).",
    )
    parser.add_argument(
        "--no-compare",
        action="store_false",
        dest="compare",
    )
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    input_dir = args.input.expanduser().resolve()
    if not input_dir.is_dir():
        raise SystemExit(f"Không thấy thư mục ảnh: {input_dir}")

    pages = parse_pages(args.pages)
    images = list_page_images(input_dir, pages)
    if not images:
        raise SystemExit(f"Không có ảnh trang (N.jpg) trong {input_dir} với --pages={args.pages!r}")

    output_dir = (args.output_dir or (input_dir / "paddleocr")).expanduser().resolve()
    model_label = f"PP-OCRv6_{args.model}"
    print(f"Model:  {model_label}")
    print(f"Engine: {args.engine}")
    print(f"Input:  {input_dir}  ({len(images)} trang)")
    print(f"Output: {output_dir}")
    print("Đang nạp model (lần đầu sẽ tải pretrained)…")
    ocr, resolved_engine = load_ocr(args.model, args.engine)
    print(f"Engine đã dùng: {resolved_engine}")

    done = 0
    skipped = 0
    for image in images:
        json_path = output_dir / f"{image.stem}-paddleocr.json"
        if args.skip_existing and json_path.exists():
            print(f"— skip {image.name}")
            skipped += 1
            continue
        print(f"→ {image.name}")
        mapping, elapsed, paddle_result = ocr_one(ocr, image)
        lines = _lines_from_mapping(mapping)
        record = build_page_record(
            source=image,
            model=f"{model_label}+{resolved_engine}",
            elapsed_s=elapsed,
            mapping=mapping,
            lines=lines,
        )
        write_outputs(
            output_dir=output_dir,
            image=image,
            record=record,
            paddle_result=paddle_result,
            save_preview=not args.no_preview,
        )
        print(f"  {record['line_count']} dòng, mean_score={record['mean_score']}, {elapsed:.1f}s")
        if args.compare:
            print_compare(image, record["result_ocr_text"])
        done += 1

    print(f"Xong: {done} trang OCR, {skipped} bỏ qua. Kết quả: {output_dir}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
