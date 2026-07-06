from __future__ import annotations

from typing import Any

import httpx

from app.hannom.client import get_auth_headers, run_image_ocr, run_transliteration, upload_image


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
        ocr_lines = run_image_ocr(
            client,
            temp_file_name=temp_file_name,
            ocr_id=ocr_id,
            lang_type=lang_type,
        )
        ocr_text = "\n".join(ocr_lines)
        transcription_lines = run_transliteration(client, text=ocr_text)

    return {
        "temp_file_name": temp_file_name,
        "ocr_lines": ocr_lines,
        "ocr_text": ocr_text,
        "transcription_lines": transcription_lines,
        "transcription_text": "\n".join(transcription_lines),
    }
