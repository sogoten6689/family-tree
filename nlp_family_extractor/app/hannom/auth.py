from __future__ import annotations

import os
from typing import Any

import httpx

from app.hannom.client import (
    DEFAULT_USER_AGENT,
    SUCCESS_CODE,
    _base_url,
    apply_runtime_token,
    get_browser_headers,
)
from app.hannom.errors import HannomApiError

TOKEN_JSON_KEYS = (
    "access_token",
    "accessToken",
    "token",
    "jwt",
    "bearer",
    "id_token",
)
TOKEN_COOKIE_NAMES = (
    "access_token",
    "token",
    "Authorization",
    "authorization",
    "jwt",
    "Bearer",
)
LOGIN_ATTEMPTS: tuple[tuple[str, dict[str, str]], ...] = (
    ("/api/web/auth/login", {"username": "{user}", "password": "{password}"}),
    ("/api/web/auth/login", {"email": "{user}", "password": "{password}"}),
    ("/api/web/login", {"username": "{user}", "password": "{password}"}),
    ("/api/web/login", {"email": "{user}", "password": "{password}"}),
    ("/api/web/user/login", {"username": "{user}", "password": "{password}"}),
)


def _looks_like_jwt(value: str) -> bool:
    cleaned = value.strip()
    if cleaned.lower().startswith("bearer "):
        cleaned = cleaned[7:].strip()
    return cleaned.count(".") >= 2 and len(cleaned) > 20


def _normalize_bearer_token(value: str) -> str:
    cleaned = value.strip()
    if cleaned.lower().startswith("bearer "):
        return cleaned[7:].strip()
    return cleaned


def _extract_token_from_json(payload: Any) -> str | None:
    if isinstance(payload, str) and _looks_like_jwt(payload):
        return _normalize_bearer_token(payload)

    if not isinstance(payload, dict):
        return None

    for key in TOKEN_JSON_KEYS:
        value = payload.get(key)
        if isinstance(value, str) and value.strip():
            return _normalize_bearer_token(value)

    for nested_key in ("data", "result", "user", "auth"):
        nested = payload.get(nested_key)
        found = _extract_token_from_json(nested)
        if found:
            return found

    return None


def _extract_token_from_cookies(cookies: httpx.Cookies) -> str | None:
    for name in TOKEN_COOKIE_NAMES:
        value = cookies.get(name)
        if isinstance(value, str) and value.strip():
            token = _normalize_bearer_token(value)
            if _looks_like_jwt(token) or len(token) >= 16:
                return token
    return None


def _parse_login_response(response: httpx.Response) -> tuple[str, str]:
    token = _extract_token_from_cookies(response.cookies)
    if token:
        return token, "cookie"

    try:
        payload = response.json()
    except ValueError as exc:
        raise HannomApiError(
            f"Đăng nhập trả về không phải JSON hợp lệ (HTTP {response.status_code}).",
            status_code=response.status_code,
        ) from exc

    if isinstance(payload, dict):
        api_code = payload.get("code")
        if api_code is not None and str(api_code) != SUCCESS_CODE:
            message = payload.get("message") or payload.get("msg") or "Đăng nhập thất bại"
            raise HannomApiError(
                str(message),
                status_code=response.status_code,
                api_code=str(api_code),
            )

    token = _extract_token_from_json(payload)
    if token:
        return token, "json_body"

    raise HannomApiError(
        "Đăng nhập thành công nhưng không tìm thấy Bearer token trong response.",
        status_code=response.status_code,
    )


def fetch_hannom_token(*, username: str, password: str) -> dict[str, Any]:
    user = username.strip()
    pwd = password.strip()
    if not user or not pwd:
        raise HannomApiError("Email/tên đăng nhập và mật khẩu Kim Hán Nôm là bắt buộc.")

    headers = get_browser_headers(include_auth=False)
    headers["Content-Type"] = "application/json"
    headers["Accept"] = "application/json"

    last_error: HannomApiError | None = None
    base = _base_url()

    with httpx.Client(headers=headers, timeout=httpx.Timeout(30.0, connect=15.0), follow_redirects=True) as client:
        for path, body_template in LOGIN_ATTEMPTS:
            body = {
                key: value.format(user=user, password=pwd)
                for key, value in body_template.items()
            }
            url = f"{base}{path}"
            try:
                response = client.post(url, json=body)
            except httpx.HTTPError as exc:
                last_error = HannomApiError(f"Không thể kết nối {url}: {exc}")
                continue

            if response.status_code >= 500:
                last_error = HannomApiError(
                    f"Kim Hán Nôm server error HTTP {response.status_code} tại {path}.",
                    status_code=response.status_code,
                )
                continue

            if response.status_code >= 400:
                detail = response.text[:300]
                try:
                    payload = response.json()
                    if isinstance(payload, dict):
                        message = payload.get("message") or payload.get("msg") or detail
                        api_code = payload.get("code")
                        last_error = HannomApiError(
                            str(message),
                            status_code=response.status_code,
                            api_code=str(api_code) if api_code is not None else None,
                        )
                        continue
                except ValueError:
                    pass
                last_error = HannomApiError(
                    f"HTTP {response.status_code} tại {path}: {detail}",
                    status_code=response.status_code,
                )
                continue

            try:
                token, source = _parse_login_response(response)
            except HannomApiError as exc:
                last_error = exc
                continue

            apply_runtime_token(token)
            return {
                "token": token,
                "source": source,
                "login_path": path,
                "username": user,
            }

    if last_error:
        raise last_error
    raise HannomApiError("Không thể đăng nhập Kim Hán Nôm với các endpoint login đã cấu hình.")


def resolve_hannom_credentials(
    *,
    email: str | None = None,
    username: str | None = None,
    password: str | None = None,
) -> tuple[str, str]:
    resolved_user = (username or email or os.getenv("HANNOM_EMAIL") or os.getenv("HANNOM_USERNAME") or "").strip()
    resolved_password = (password or os.getenv("HANNOM_PASSWORD") or "").strip()
    return resolved_user, resolved_password


def get_token_status() -> dict[str, Any]:
    env_token = os.getenv("HANNOM_API_TOKEN", "").strip()
    from app.hannom.client import get_cached_token

    cached = get_cached_token()
    active = env_token or cached
    preview = None
    source = "none"
    if env_token:
        source = "env"
        preview = _mask_token(env_token)
    elif cached:
        source = "runtime_cache"
        preview = _mask_token(cached)

    return {
        "configured": bool(active),
        "source": source,
        "preview": preview,
        "token_length": len(active) if active else 0,
    }


def _mask_token(token: str) -> str:
    cleaned = _normalize_bearer_token(token)
    if len(cleaned) <= 12:
        return "*" * len(cleaned)
    return f"{cleaned[:8]}...{cleaned[-4:]}"
