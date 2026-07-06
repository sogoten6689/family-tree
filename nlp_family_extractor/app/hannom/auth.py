from __future__ import annotations

import os
import re
from typing import Any
from urllib.parse import unquote

import httpx

from app.hannom.client import (
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
    "token",
    "access_token",
    "Authorization",
    "authorization",
    "jwt",
    "Bearer",
)
ACCOUNT_LOGIN_PATH = "/account/login"


def _looks_like_jwt(value: str) -> bool:
    cleaned = value.strip()
    if cleaned.lower().startswith("bearer "):
        cleaned = cleaned[7:].strip()
    return cleaned.count(".") >= 2 and len(cleaned) > 20


def _normalize_bearer_token(value: str) -> str:
    cleaned = unquote(value.strip())
    if cleaned.lower().startswith("bearer "):
        return cleaned[7:].strip()
    return cleaned


def _extract_csrf_token(html: str) -> str | None:
    patterns = (
        r'name="__RequestVerificationToken"\s+type="hidden"\s+value="([^"]+)"',
        r'name="__RequestVerificationToken"\s+value="([^"]+)"',
        r'value="([^"]+)"\s+name="__RequestVerificationToken"',
    )
    for pattern in patterns:
        match = re.search(pattern, html, flags=re.IGNORECASE)
        if match:
            return match.group(1)
    return None


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


def _extract_token_from_cookie_jar(cookies: httpx.Cookies) -> tuple[str, str] | None:
    for name in TOKEN_COOKIE_NAMES:
        value = cookies.get(name)
        if not isinstance(value, str) or not value.strip():
            continue
        token = _normalize_bearer_token(value)
        if _looks_like_jwt(token) or len(token) >= 16:
            return token, f"cookie:{name}"
    return None


def _extract_login_error(html: str) -> str | None:
    match = re.search(
        r'class="[^"]*field-validation-error[^"]*"[^>]*>([^<]+)<',
        html,
        flags=re.IGNORECASE,
    )
    if match:
        message = match.group(1).strip()
        if message:
            return message
    if "Invalid login attempt" in html:
        return "Invalid login attempt"
    return None


def _login_via_account_form(client: httpx.Client, *, username: str, password: str) -> tuple[str, str]:
    base = _base_url()
    login_url = f"{base}{ACCOUNT_LOGIN_PATH}"

    page = client.get(login_url)
    if page.status_code >= 400:
        raise HannomApiError(
            f"Không thể mở trang đăng nhập Kim Hán Nôm (HTTP {page.status_code}).",
            status_code=page.status_code,
        )

    form_data: dict[str, str] = {
        "UserName": username,
        "Password": password,
    }
    csrf = _extract_csrf_token(page.text)
    if csrf:
        form_data["__RequestVerificationToken"] = csrf

    response = client.post(
        login_url,
        data=form_data,
        headers={
            "Content-Type": "application/x-www-form-urlencoded",
            "Referer": login_url,
            "Origin": base,
        },
    )

    token_info = _extract_token_from_cookie_jar(client.cookies)
    if token_info:
        return token_info

    if response.headers.get("content-type", "").startswith("application/json"):
        try:
            payload = response.json()
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
        except ValueError:
            pass

    login_error = _extract_login_error(response.text)
    if login_error:
        raise HannomApiError(f"Đăng nhập thất bại: {login_error}", status_code=response.status_code)

    if ACCOUNT_LOGIN_PATH in str(response.url):
        raise HannomApiError(
            "Đăng nhập không thành công. Kiểm tra lại tên đăng nhập/mật khẩu Kim Hán Nôm.",
            status_code=response.status_code,
        )

    raise HannomApiError(
        "Đăng nhập xong nhưng không tìm thấy cookie `token`. "
        "Hãy đăng nhập thủ công trên kimhannom.fit.hcmus.edu.vn và copy cookie `token`.",
        status_code=response.status_code,
    )


def fetch_hannom_token(*, username: str, password: str) -> dict[str, Any]:
    user = username.strip()
    pwd = password.strip()
    if not user or not pwd:
        raise HannomApiError("Email/tên đăng nhập và mật khẩu Kim Hán Nôm là bắt buộc.")

    headers = get_browser_headers(include_auth=False)
    headers["Accept"] = "text/html,application/xhtml+xml,application/json;q=0.9,*/*;q=0.8"

    with httpx.Client(
        headers=headers,
        timeout=httpx.Timeout(30.0, connect=15.0),
        follow_redirects=True,
    ) as client:
        token, source = _login_via_account_form(client, username=user, password=pwd)

    apply_runtime_token(token)
    return {
        "token": token,
        "source": source,
        "login_path": ACCOUNT_LOGIN_PATH,
        "username": user,
    }


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
