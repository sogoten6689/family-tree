"""Harness tích hợp: chạy API thật qua HTTP (không dùng TestClient).

Hai chế độ:
- Mặc định: tự khởi động ``uvicorn api:app`` ở cổng trống, KHÔNG có MySQL (giống CI).
- ``HARNESS_API_URL=http://host:port``: nhắm vào stack đã chạy (vd. docker compose có MySQL).
  Khi đó test cần DB (marker ``requires_db``) tự chạy nếu ``/health`` báo có DB.
"""
from __future__ import annotations

import os
import socket
import subprocess
import sys
import time
from pathlib import Path
from typing import Iterator

import httpx
import pytest

BACKEND_ROOT = Path(__file__).resolve().parents[2]
ADMIN_EMAIL = os.getenv("ADMIN_EMAIL", "admin@giapha.com")
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "Admin@123456")
STARTUP_TIMEOUT_S = 90


def pytest_configure(config: pytest.Config) -> None:
    config.addinivalue_line("markers", "requires_db: cần API có MySQL (đặt HARNESS_API_URL trỏ vào stack docker)")


def _free_port() -> int:
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]


def _wait_ready(base: str, proc: subprocess.Popen | None) -> None:
    deadline = time.time() + STARTUP_TIMEOUT_S
    while time.time() < deadline:
        if proc is not None and proc.poll() is not None:
            raise RuntimeError(f"uvicorn thoát sớm (mã {proc.returncode})")
        try:
            if httpx.get(f"{base}/health", timeout=2).status_code == 200:
                return
        except httpx.HTTPError:
            pass
        time.sleep(0.5)
    raise RuntimeError(f"API không sẵn sàng sau {STARTUP_TIMEOUT_S}s tại {base}")


@pytest.fixture(scope="session")
def api_base(tmp_path_factory: pytest.TempPathFactory) -> Iterator[str]:
    external = os.getenv("HARNESS_API_URL")
    if external:
        base = external.rstrip("/")
        _wait_ready(base, None)
        yield base
        return

    port = _free_port()
    log_path = tmp_path_factory.mktemp("harness") / "uvicorn.log"
    env = {**os.environ, "PYTHONPATH": str(BACKEND_ROOT), "JWT_SECRET_KEY": "harness-secret"}
    for key in ("MYSQL_HOST", "MYSQL_USER", "MYSQL_PASSWORD"):
        env[key] = ""  # tắt DB, tránh đọc nhầm .env máy local
    with log_path.open("w") as log:
        proc = subprocess.Popen(
            [sys.executable, "-m", "uvicorn", "api:app", "--host", "127.0.0.1", "--port", str(port)],
            cwd=BACKEND_ROOT, env=env, stdout=log, stderr=subprocess.STDOUT,
        )
        base = f"http://127.0.0.1:{port}"
        try:
            _wait_ready(base, proc)
            yield base
        except RuntimeError as exc:
            raise RuntimeError(f"{exc}\n--- uvicorn.log ---\n{log_path.read_text()[-3000:]}") from exc
        finally:
            proc.terminate()
            try:
                proc.wait(timeout=10)
            except subprocess.TimeoutExpired:
                proc.kill()


@pytest.fixture(scope="session")
def client(api_base: str) -> Iterator[httpx.Client]:
    with httpx.Client(base_url=api_base, timeout=30) as http:
        yield http


@pytest.fixture(scope="session")
def db_enabled(client: httpx.Client) -> bool:
    """Có MySQL hay không: đăng nhập sai trả 401 (có DB) thay vì 503 (không DB)."""
    resp = client.post("/api/login", json={"email": "nobody@harness.invalid", "password": "x"})
    return resp.status_code != 503


@pytest.fixture(scope="session")
def admin_headers(client: httpx.Client, db_enabled: bool) -> dict[str, str]:
    if not db_enabled:
        pytest.skip("API không có MySQL — dùng HARNESS_API_URL trỏ vào stack docker")
    resp = client.post("/api/login", json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD})
    assert resp.status_code == 200, f"đăng nhập admin thất bại: {resp.status_code} {resp.text}"
    return {"Authorization": f"Bearer {resp.json()['access_token']}"}
