from __future__ import annotations

import logging
import queue
import threading
from dataclasses import dataclass, field
from typing import Any, Callable, ContextManager, Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

# Chạy engine phiên âm/dịch nghĩa NỀN: tool kiểu điều khiển trình duyệt mất
# hàng phút/lần và chỉ chạy 1 việc 1 lúc → mỗi engine 1 thread worker xử lý
# tuần tự, request trả về ngay. Trạng thái theo dõi bằng chính
# gia_pha_version_step (transliteration/translation): pending → running →
# done | error, không cần bảng job riêng.

logger = logging.getLogger(__name__)

SOURCE_PREFIX = "engine-"
# Đã chốt 2026-10-02: kết quả engine KHÔNG cần duyệt → vào thẳng dữ liệu
# train. Muốn đi qua luồng duyệt như file nhập thì đổi thành "pending".
ENGINE_RESULT_REVIEW_STATUS = "approved"
DEFAULT_PAGE_TIMEOUT_SECONDS = 600.0

SessionFactory = Callable[[], ContextManager[Session]]


@dataclass
class EngineJob:
    scan_id: int
    version_id: int
    engine: str
    pages: list[tuple[int, str]]  # (page_number, hannom_text)
    page_ids: dict[int, int] = field(default_factory=dict)


def _default_session_factory() -> ContextManager[Session]:
    from app.database import session_scope  # đã là @contextmanager

    return session_scope()


def _call_with_timeout(fn: Callable[[], Any], timeout: float) -> Any:
    """Chạy fn trong thread riêng, chờ tối đa `timeout` giây. Python không
    huỷ được thread đang chạy: nếu quá giờ, lời gọi bị bỏ lại (có thể vẫn
    giữ trình duyệt bận) và job này báo lỗi."""
    box: dict[str, Any] = {}

    def target() -> None:
        try:
            box["result"] = fn()
        except BaseException as error:  # noqa: BLE001 — chuyển lỗi về worker
            box["error"] = error

    thread = threading.Thread(target=target, daemon=True)
    thread.start()
    thread.join(timeout)
    if thread.is_alive():
        raise TimeoutError(f"quá {timeout:.0f}s")
    if "error" in box:
        raise box["error"]
    return box.get("result")


class TextEngineRunner:
    def __init__(
        self,
        session_factory: SessionFactory = _default_session_factory,
        page_timeout: float = DEFAULT_PAGE_TIMEOUT_SECONDS,
    ) -> None:
        self._session_factory = session_factory
        self._page_timeout = page_timeout
        self._queues: dict[str, queue.Queue[EngineJob]] = {}
        self._lock = threading.Lock()

    def submit(self, job: EngineJob) -> None:
        with self._lock:
            jobs = self._queues.get(job.engine)
            if jobs is None:
                jobs = queue.Queue()
                self._queues[job.engine] = jobs
                threading.Thread(target=self._worker, args=(jobs,), name=f"text-engine-{job.engine}", daemon=True).start()
        jobs.put(job)

    def wait_idle(self) -> None:
        """Chờ mọi job đã nộp chạy xong (dùng trong test)."""
        for jobs in list(self._queues.values()):
            jobs.join()

    def _worker(self, jobs: queue.Queue[EngineJob]) -> None:
        while True:
            job = jobs.get()
            try:
                self._run(job)
            except Exception:  # noqa: BLE001 — worker không được chết
                logger.exception("text engine job %s lỗi ngoài dự kiến", job.version_id)
            finally:
                jobs.task_done()

    def _run(self, job: EngineJob) -> None:
        from app.hannom.text_engines import TEXT_ENGINE_REGISTRY
        from app.workspace.llm_import import add_coverage_warnings, parse_import
        from app.workspace.repository import GiaPhaVersionRepository

        with self._session_factory() as db:
            GiaPhaVersionRepository(db).set_text_steps(job.version_id, "running", started=True)

        fn = TEXT_ENGINE_REGISTRY.get(job.engine)
        records: list[dict[str, Any]] = []
        try:
            if fn is None:
                raise RuntimeError(f"engine '{job.engine}' không còn được đăng ký")
            for page_number, hannom_text in job.pages:
                output = _call_with_timeout(
                    lambda text=hannom_text, number=page_number: fn(text, page_number=number), self._page_timeout
                )
                if not isinstance(output, list):
                    raise TypeError(f"trang {page_number}: engine phải trả về list, nhận {type(output).__name__}")
                records += [{**row, "page": page_number} if isinstance(row, dict) else row for row in output]
        except Exception as error:  # noqa: BLE001 — lỗi adapter của người dùng
            self._fail(job, f"{type(error).__name__}: {error}")
            return

        parsed = parse_import({"source": SOURCE_PREFIX + job.engine, "records": records}, set(job.page_ids))
        if parsed.errors:
            self._fail(job, "Kết quả engine không hợp lệ: " + "; ".join(parsed.errors[:5]))
            return
        add_coverage_warnings(parsed, dict(job.pages))
        with self._session_factory() as db:
            versions = GiaPhaVersionRepository(db)
            versions.apply_page_records(
                job.version_id,
                {n: [{"cn": r.cn, "sv": r.sv, "vi": r.vi} for r in recs] for n, recs in parsed.pages.items()},
                job.page_ids,
            )
            version = versions.get(job.version_id)
            if version is not None:
                version.note = (
                    f"{job.engine}: {parsed.record_count} câu / {len(parsed.pages)} trang"
                    + (f", {len(parsed.warnings)} cảnh báo độ khớp OCR" if parsed.warnings else "")
                )[:255]
                db.add(version)
            versions.set_text_steps(job.version_id, "done", finished=True)

    def _fail(self, job: EngineJob, message: str) -> None:
        from app.workspace.repository import GiaPhaVersionRepository

        with self._session_factory() as db:
            GiaPhaVersionRepository(db).set_text_steps(job.version_id, "error", error_message=message, finished=True)


def fail_interrupted_runs(db: Session) -> int:
    """Khi server khởi động: job trong hàng đợi (bộ nhớ) đã mất → mọi bước
    pending/running của version do engine tạo chuyển sang error, tránh treo."""
    from app.workspace.models import GiaPhaVersion, GiaPhaVersionStep
    from app.workspace.repository import TEXT_STEP_TYPES

    stmt = (
        select(GiaPhaVersionStep)
        .join(GiaPhaVersion, GiaPhaVersion.id == GiaPhaVersionStep.version_id)
        .where(
            GiaPhaVersion.source.like(SOURCE_PREFIX + "%"),
            GiaPhaVersionStep.step_type.in_(TEXT_STEP_TYPES),
            GiaPhaVersionStep.status.in_(("pending", "running")),
        )
    )
    steps = list(db.scalars(stmt).all())
    for step in steps:
        step.status = "error"
        step.error_message = "Server khởi động lại khi job đang chờ/chạy — hãy chạy lại."
        db.add(step)
    db.commit()
    return len(steps)


_runner: Optional[TextEngineRunner] = None


def get_runner() -> TextEngineRunner:
    global _runner
    if _runner is None:
        _runner = TextEngineRunner()
    return _runner
