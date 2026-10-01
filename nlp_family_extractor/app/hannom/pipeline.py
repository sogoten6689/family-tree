from __future__ import annotations

from typing import Any

import httpx

from app.hannom.client import (
    _coerce_text_list,
    get_auth_headers,
    normalize_result_bbox,
    run_image_ocr_payload,
    run_transliteration,
    upload_image,
)
from app.hannom.errors import HannomApiError


def process_hannom_image_to_vietnamese(
    file_bytes: bytes,
    filename: str,
    *,
    ocr_id: int | None = None,
    lang_type: int | None = None,
) -> dict[str, Any]:
    """
    Pipeline 3 bước: upload ảnh → OCR Hán/Nôm → phiên âm Quốc ngữ.
    """
    if not file_bytes:
        raise ValueError("File ảnh rỗng.")
    if not filename.strip():
        raise ValueError("Tên file không hợp lệ.")

    headers = get_auth_headers()
    timeout = httpx.Timeout(120.0, connect=20.0)

    with httpx.Client(headers=headers, timeout=timeout) as client:
        temp_file_name = upload_image(client, file_bytes, filename)
        ocr_payload = run_image_ocr_payload(
            client,
            temp_file_name=temp_file_name,
            ocr_id=ocr_id,
            lang_type=lang_type,
        )
        ocr_lines = _coerce_text_list(ocr_payload, keys=("result_ocr_text", "ocr_text", "text"))
        if not ocr_lines:
            raise HannomApiError("OCR không trả về văn bản nào.")
        bbox = normalize_result_bbox(ocr_payload.get("result_bbox"))
        ocr_text = "\n".join(ocr_lines)
        transcription_lines = run_transliteration(client, text=ocr_text)

    return {
        "temp_file_name": temp_file_name,
        "ocr_lines": ocr_lines,
        "ocr_text": ocr_text,
        "transcription_lines": transcription_lines,
        "transcription_text": "\n".join(transcription_lines),
        "bbox": bbox,
    }


def process_hannom_image_v2(
    file_bytes: bytes,
    filename: str,
    *,
    ocr_id: int | None = None,
    lang_type: int | None = None,
    engine_names: list[str] | None = None,
) -> dict[str, Any]:
    """
    Pipeline v2: upload ảnh → OCR nhiều engine (registry, đọc engine_names từ
    setting HANNOM_VOTE_ENGINES nếu không truyền rõ) → vote → phiên âm Quốc
    ngữ (trên text đã vote) → dịch nghĩa Quốc ngữ hiện đại (Gemini).

    Với đúng 2 engine (mặc định kimhannom + gemini_vision), luật "ép số lẻ"
    của thuật toán vote sẽ loại 1 engine khỏi vòng vote để tránh hoà 1-1 —
    kết quả là chọn nguyên văn của engine giống "đa số" hơn, CHƯA vote thật
    theo từng dòng (chỉ có từ 3 engine trở lên). Đây là hành vi đúng thiết
    kế của thuật toán (xem app/hannom/vote.py), không phải bug.
    """
    if not file_bytes:
        raise ValueError("File ảnh rỗng.")
    if not filename.strip():
        raise ValueError("Tên file không hợp lệ.")

    from app.config import get_hannom_vote_engines
    from app.hannom.engines import ENGINE_REGISTRY, EngineResult
    from app.hannom.translate import translate_to_modern_vietnamese
    from app.hannom.vote import vote_from_results

    names = engine_names or get_hannom_vote_engines()
    results: dict[str, EngineResult] = {}
    for name in names:
        adapter = ENGINE_REGISTRY.get(name)
        if adapter is None:
            continue
        if name == "kimhannom":
            result = adapter(file_bytes, filename, ocr_id=ocr_id, lang_type=lang_type)
        else:
            result = adapter(file_bytes, filename)
        if result is not None:
            results[name] = result

    if not results:
        raise HannomApiError("Không engine OCR nào thành công (kiểm tra cấu hình/kết nối).")

    vote_result = vote_from_results(results, priority=names)
    voted_text = str(vote_result.get("voted_text") or "")
    if not voted_text.strip():
        raise HannomApiError("OCR không trả về văn bản nào.")

    bbox = results["kimhannom"].bbox if "kimhannom" in results else None

    headers = get_auth_headers()
    timeout = httpx.Timeout(120.0, connect=20.0)
    with httpx.Client(headers=headers, timeout=timeout) as client:
        transcription_lines = run_transliteration(client, text=voted_text)
    transcription_text = "\n".join(transcription_lines)

    translation_text, translation_error = translate_to_modern_vietnamese(transcription_text, voted_text)

    return {
        "pipeline_version": "v2",
        "engines_used": list(results.keys()),
        "ocr_lines": voted_text.splitlines(),
        "ocr_text": voted_text,
        "transcription_lines": transcription_lines,
        "transcription_text": transcription_text,
        "translation_text": translation_text,
        "translation_error": translation_error,
        "bbox": bbox,
        "vote_meta": {
            key: vote_result.get(key)
            for key in ("vote_method", "engines", "uncertain_spans", "uncertain_rate", "structural_diffs")
        },
    }


def run_hannom_pipeline(
    file_bytes: bytes,
    filename: str,
    *,
    ocr_id: int | None = None,
    lang_type: int | None = None,
) -> dict[str, Any]:
    """Điểm nối chung duy nhất cho cả 2 nơi gọi pipeline OCR ảnh
    (app/documents/repository.py:_ocr_transliterate_bytes và
    api.py:analyze_family_image) — tự chọn v1/v2 theo setting
    HANNOM_PIPELINE_VERSION, tự resolve ocr_id/lang_type mặc định từ setting
    HANNOM_LAB_* nếu caller không truyền rõ. Trả dict superset của v1 (thêm
    key mới với giá trị mặc định None/[] để caller không cần biết v1/v2)."""
    from app.config import get_hannom_lab_lang_type, get_hannom_lab_ocr_id, get_hannom_pipeline_version

    resolved_ocr_id = ocr_id if ocr_id is not None else get_hannom_lab_ocr_id()
    resolved_lang_type = lang_type if lang_type is not None else get_hannom_lab_lang_type()

    if get_hannom_pipeline_version() == "v2":
        return process_hannom_image_v2(
            file_bytes, filename, ocr_id=resolved_ocr_id, lang_type=resolved_lang_type
        )

    result = process_hannom_image_to_vietnamese(
        file_bytes, filename, ocr_id=resolved_ocr_id, lang_type=resolved_lang_type
    )
    result.setdefault("pipeline_version", "v1")
    result.setdefault("translation_text", None)
    result.setdefault("vote_meta", None)
    result.setdefault("engines_used", ["kimhannom"])
    return result
