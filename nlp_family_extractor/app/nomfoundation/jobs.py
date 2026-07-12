from __future__ import annotations

import json
import threading
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Dict, Optional

_JOBS_LOCK = threading.Lock()
_JOBS: Dict[str, Dict[str, Any]] = {}


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _jobs_dir(output_dir: Path) -> Path:
    path = output_dir / "jobs"
    path.mkdir(parents=True, exist_ok=True)
    return path


def _persist_job(output_dir: Path, job: Dict[str, Any]) -> None:
    job_path = _jobs_dir(output_dir) / f"{job['job_id']}.json"
    job_path.write_text(json.dumps(job, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def get_job(output_dir: Path, job_id: str) -> Optional[Dict[str, Any]]:
    with _JOBS_LOCK:
        if job_id in _JOBS:
            return dict(_JOBS[job_id])

    job_path = _jobs_dir(output_dir) / f"{job_id}.json"
    if not job_path.exists():
        return None
    try:
        return json.loads(job_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None


def _update_job(output_dir: Path, job_id: str, **fields: Any) -> Dict[str, Any]:
    with _JOBS_LOCK:
        job = dict(_JOBS.get(job_id) or {})
        if not job:
            job_path = _jobs_dir(output_dir) / f"{job_id}.json"
            if job_path.exists():
                try:
                    job = json.loads(job_path.read_text(encoding="utf-8"))
                except (OSError, json.JSONDecodeError):
                    job = {"job_id": job_id}
        job.update(fields)
        job["updated_at"] = _now_iso()
        _JOBS[job_id] = job
        _persist_job(output_dir, job)
        return job


def start_nom_import_job(
    *,
    output_dir: Path,
    params: Dict[str, Any],
    runner: Callable[[str, Dict[str, Any]], Dict[str, Any]],
) -> Dict[str, Any]:
    job_id = uuid.uuid4().hex
    job = {
        "job_id": job_id,
        "status": "queued",
        "type": "nom_import",
        "params": params,
        "progress": {},
        "result": None,
        "error": None,
        "created_at": _now_iso(),
        "updated_at": _now_iso(),
    }
    with _JOBS_LOCK:
        _JOBS[job_id] = job
    _persist_job(output_dir, job)

    def _run() -> None:
        _update_job(output_dir, job_id, status="running")
        try:
            result = runner(job_id, params)
            _update_job(output_dir, job_id, status="done", result=result, progress=result.get("progress", {}))
        except Exception as exc:
            _update_job(output_dir, job_id, status="error", error=str(exc))

    thread = threading.Thread(target=_run, daemon=True, name=f"nom-import-{job_id[:8]}")
    thread.start()
    return job
