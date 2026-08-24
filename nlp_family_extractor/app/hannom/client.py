from __future__ import annotations

import os
import threading
import time
from collections import deque
from typing import Any

import httpx

from app.hannom.errors import HannomApiError

DEFAULT_BASE_URL = "https://kimhannom.fit.hcmus.edu.vn"
DEFAULT_USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/122.0.0.0 Safari/537.36"
)
SUCCESS_CODE = "000000"

_cached_runtime_token: str | None = None

_rate_lock = threading.Lock()
_request_timestamps: deque[float] = deque()


def _base_url() -> str:
    return os.getenv("HANNOM_API_BASE_URL", DEFAULT_BASE_URL).rstrip("/")


def _rate_limit_per_minute() -> int:
    return max(1, int(os.getenv("HANNOM_RATE_LIMIT_PER_MINUTE", "40")))


def _min_interval_seconds() -> float:
    override = os.getenv("HANNOM_REQUEST_DELAY_SECONDS")
    if override:
        return max(0.0, float(override))
    return 60.0 / _rate_limit_per_minute()


def get_cached_token() -> str | None:
    return _cached_runtime_token


def apply_runtime_token(token: str | None) -> None:
    global _cached_runtime_token
    cleaned = (token or "").strip()
    if cleaned.lower().startswith("bearer "):
        cleaned = cleaned[7:].strip()
    _cached_runtime_token = cleaned or None
    if cleaned:
        os.environ["HANNOM_API_TOKEN"] = cleaned


def get_browser_headers(*, include_auth: bool = True) -> dict[str, str]:
    headers = {
        "User-Agent": os.getenv("HANNOM_USER_AGENT", DEFAULT_USER_AGENT),
        "Accept": "application/json",
    }
    if include_auth:
        headers["Authorization"] = f"Bearer {get_effective_token()}"
    return headers


def get_effective_token() -> str:
    env_token = os.getenv("HANNOM_API_TOKEN", "").strip()
    if env_token:
        return env_token.lstrip("Bearer ").strip()

    from app.hannom.credential_store import get_credential_store

    db_token = get_credential_store().get_valid_token()
    if db_token:
        apply_runtime_token(db_token)
        return db_token

    if _cached_runtime_token:
        return _cached_runtime_token
    raise HannomApiError(
        "HANNOM_API_TOKEN chưa được cấu hình. "
        "Lưu tài khoản qua PUT /api/developer/hannom/credentials, "
        "gọi POST /api/developer/hannom/fetch-token, hoặc thiết lập biến môi trường.",
    )


def get_auth_headers() -> dict[str, str]:
    return get_browser_headers(include_auth=True)


def _wait_for_rate_limit() -> None:
    interval = _min_interval_seconds()
    with _rate_lock:
        now = time.monotonic()
        window_start = now - 60.0
        while _request_timestamps and _request_timestamps[0] < window_start:
            _request_timestamps.popleft()

        limit = _rate_limit_per_minute()
        if len(_request_timestamps) >= limit:
            sleep_for = _request_timestamps[0] + 60.0 - now
            if sleep_for > 0:
                time.sleep(sleep_for)
            now = time.monotonic()
            window_start = now - 60.0
            while _request_timestamps and _request_timestamps[0] < window_start:
                _request_timestamps.popleft()

        if _request_timestamps:
            since_last = now - _request_timestamps[-1]
            if since_last < interval:
                time.sleep(interval - since_last)

        _request_timestamps.append(time.monotonic())


def _extract_payload(response_json: Any) -> Any:
    if not isinstance(response_json, dict):
        raise HannomApiError("Phản hồi API không hợp lệ (không phải JSON object).")

    api_code = response_json.get("code")
    if api_code is not None and str(api_code) != SUCCESS_CODE:
        message = response_json.get("message") or response_json.get("msg") or "Kim Hán Nôm API error"
        raise HannomApiError(
            str(message),
            api_code=str(api_code),
        )

    if "data" in response_json:
        return response_json["data"]
    return response_json


def _request_json(
    client: httpx.Client,
    method: str,
    path: str,
    *,
    json_body: dict[str, Any] | None = None,
    files: dict[str, tuple[str, bytes, str]] | None = None,
) -> Any:
    _wait_for_rate_limit()
    url = f"{_base_url()}{path}"

    try:
        response = client.request(method, url, json=json_body, files=files)
    except httpx.HTTPError as exc:
        raise HannomApiError(f"Không thể kết nối Kim Hán Nôm API: {exc}") from exc

    if response.status_code == 401:
        from app.hannom.credential_store import get_credential_store

        refreshed = get_credential_store().force_refresh()
        if refreshed:
            apply_runtime_token(refreshed)
            client.headers["Authorization"] = f"Bearer {refreshed}"
            _wait_for_rate_limit()
            try:
                response = client.request(method, url, json=json_body, files=files)
            except httpx.HTTPError as exc:
                raise HannomApiError(f"Không thể kết nối Kim Hán Nôm API: {exc}") from exc

    if response.status_code >= 400:
        detail = response.text[:500]
        try:
            body = response.json()
            if isinstance(body, dict):
                api_code = body.get("code")
                message = body.get("message") or body.get("msg") or detail
                raise HannomApiError(
                    str(message),
                    status_code=response.status_code,
                    api_code=str(api_code) if api_code is not None else None,
                )
        except ValueError:
            pass
        raise HannomApiError(
            f"HTTP {response.status_code}: {detail}",
            status_code=response.status_code,
        )

    try:
        response_json = response.json()
    except ValueError as exc:
        raise HannomApiError("Phản hồi API không phải JSON hợp lệ.") from exc

    return _extract_payload(response_json)


def upload_image(client: httpx.Client, file_bytes: bytes, filename: str) -> str:
    payload = _request_json(
        client,
        "POST",
        "/api/web/clc-sinonom/image-upload",
        files={"image_file": (filename, file_bytes, _guess_content_type(filename))},
    )

    if isinstance(payload, dict):
        temp_name = payload.get("file_name") or payload.get("filename")
        if temp_name:
            return str(temp_name)

    if isinstance(payload, str) and payload.strip():
        return payload.strip()

    raise HannomApiError("Upload ảnh thành công nhưng không nhận được file_name.")


def run_image_ocr(
    client: httpx.Client,
    *,
    temp_file_name: str,
    ocr_id: int | None = None,
    lang_type: int | None = None,
    epitaph: int = 0,
    tag: str | None = None,
) -> list[str]:
    payload = run_image_ocr_payload(
        client,
        temp_file_name=temp_file_name,
        ocr_id=ocr_id,
        lang_type=lang_type,
        epitaph=epitaph,
        tag=tag,
    )
    texts = _coerce_text_list(payload, keys=("result_ocr_text", "ocr_text", "text"))
    if not texts:
        raise HannomApiError("OCR không trả về văn bản nào.")
    return texts


def run_image_ocr_payload(
    client: httpx.Client,
    *,
    temp_file_name: str,
    ocr_id: int | None = None,
    lang_type: int | None = None,
    epitaph: int = 0,
    tag: str | None = None,
) -> dict[str, Any]:
    """Full image-ocr `data` object, including result_bbox when the API sends it."""
    body = {
        "ocr_id": ocr_id if ocr_id is not None else int(os.getenv("HANNOM_OCR_ID", "1")),
        "lang_type": lang_type if lang_type is not None else int(os.getenv("HANNOM_OCR_LANG_TYPE", "0")),
        "epitaph": epitaph,
        "tag": tag,
        "file_name": temp_file_name,
    }
    payload = _request_json(
        client,
        "POST",
        "/api/web/clc-sinonom/image-ocr",
        json_body=body,
    )
    if isinstance(payload, dict):
        return payload
    texts = _coerce_text_list(payload, keys=("result_ocr_text", "ocr_text", "text"))
    return {"result_ocr_text": texts, "result_bbox": []}


def run_transliteration(
    client: httpx.Client,
    *,
    text: str,
    font_type: int | None = None,
    lang_type: int | None = None,
) -> list[str]:
    body = {
        "text": text,
        "font_type": font_type if font_type is not None else int(os.getenv("HANNOM_FONT_TYPE", "1")),
        "lang_type": lang_type
        if lang_type is not None
        else int(os.getenv("HANNOM_TRANSLITERATION_LANG_TYPE", "1")),
    }
    payload = _request_json(
        client,
        "POST",
        "/api/web/clc-sinonom/sinonom-transliteration",
        json_body=body,
    )

    texts = _coerce_text_list(payload, keys=("result_text_transcription", "transcription", "text"))
    if not texts:
        raise HannomApiError("Phiên âm không trả về kết quả nào.")
    return texts


def _coerce_text_list(payload: Any, *, keys: tuple[str, ...]) -> list[str]:
    if isinstance(payload, list):
        return [str(item).strip() for item in payload if str(item).strip()]

    if isinstance(payload, dict):
        for key in keys:
            value = payload.get(key)
            if isinstance(value, list):
                return [str(item).strip() for item in value if str(item).strip()]
            if isinstance(value, str) and value.strip():
                return [value.strip()]

    if isinstance(payload, str) and payload.strip():
        return [payload.strip()]

    return []


def _guess_content_type(filename: str) -> str:
    lowered = filename.lower()
    if lowered.endswith(".png"):
        return "image/png"
    if lowered.endswith(".webp"):
        return "image/webp"
    if lowered.endswith(".gif"):
        return "image/gif"
    if lowered.endswith(".bmp"):
        return "image/bmp"
    return "image/jpeg"
