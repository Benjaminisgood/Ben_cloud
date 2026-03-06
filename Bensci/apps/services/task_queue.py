from __future__ import annotations

import json
import time
from collections.abc import Callable
from concurrent.futures import Future, ThreadPoolExecutor
from contextvars import ContextVar
from datetime import datetime
from threading import Event, Lock, Thread
from typing import Any
from uuid import uuid4

from sqlalchemy import case, func, select, update

from apps.core.config import settings
from apps.db.models import Task
from apps.db.session import SessionLocal

TaskHandler = Callable[[dict[str, Any], Callable[[str], None]], dict[str, Any] | None]

_TASK_HANDLERS: dict[str, TaskHandler] = {}
_TASK_HANDLER_LOCK = Lock()
_CURRENT_TASK_ID: ContextVar[str | None] = ContextVar("current_task_id", default=None)
_TERMINAL_STATUSES = {"completed", "failed", "cancelled"}


class TaskWorker:
    def __init__(self, *, max_workers: int, poll_interval_seconds: float) -> None:
        self.max_workers = max(1, int(max_workers))
        self.poll_interval_seconds = max(0.1, float(poll_interval_seconds))
        self._stop_event = Event()
        self._thread: Thread | None = None
        self._executor = ThreadPoolExecutor(max_workers=self.max_workers, thread_name_prefix="task-worker")
        self._futures: dict[Future[None], str] = {}

    def start(self) -> None:
        if self._thread is not None and self._thread.is_alive():
            return
        self._stop_event.clear()
        self._thread = Thread(target=self._run_loop, daemon=True, name="task-worker-loop")
        self._thread.start()

    def stop(self) -> None:
        self._stop_event.set()
        if self._thread is not None:
            self._thread.join(timeout=5)
        self._executor.shutdown(wait=False)

    def _run_loop(self) -> None:
        while not self._stop_event.is_set():
            self._cleanup_futures()
            available_slots = self.max_workers - len(self._futures)
            if available_slots > 0:
                claimed = _claim_queued_tasks(limit=available_slots)
                for task_id in claimed:
                    future = self._executor.submit(_execute_task, task_id)
                    self._futures[future] = task_id

            self._stop_event.wait(self.poll_interval_seconds)

        # Best-effort drain state on shutdown.
        self._cleanup_futures()

    def _cleanup_futures(self) -> None:
        done: list[Future[None]] = []
        for future in self._futures:
            if future.done():
                done.append(future)
        for future in done:
            self._futures.pop(future, None)
            try:
                future.result()
            except Exception:
                # task execution errors are already recorded in DB
                pass


_WORKER: TaskWorker | None = None
_WORKER_LOCK = Lock()


def _now_utc() -> datetime:
    return datetime.utcnow()


def _loads_json(raw: str | None) -> dict[str, Any]:
    if not raw:
        return {}
    try:
        data = json.loads(raw)
        if isinstance(data, dict):
            return data
        return {}
    except Exception:
        return {}


def _dumps_json(data: dict[str, Any] | None) -> str:
    payload = data or {}
    return json.dumps(payload, ensure_ascii=False)


def register_task_handler(task_type: str, handler: TaskHandler) -> None:
    key = (task_type or "").strip()
    if not key:
        raise ValueError("task_type 不能为空")
    with _TASK_HANDLER_LOCK:
        _TASK_HANDLERS[key] = handler


def get_current_task_id() -> str | None:
    return _CURRENT_TASK_ID.get()


def append_task_log(task_id: str, message: str) -> None:
    line = f"[{datetime.now().strftime('%H:%M:%S')}] {message}"
    session = SessionLocal()
    try:
        existing = func.coalesce(Task.log_text, "")
        next_log = case(
            (existing == "", line),
            else_=existing + "\n" + line,
        )
        result = session.execute(
            update(Task)
            .where(Task.id == task_id)
            .values(
                log_text=next_log,
                updated_at=_now_utc(),
            )
        )
        if result.rowcount != 1:
            session.rollback()
            return
        session.commit()
    except Exception:
        session.rollback()
    finally:
        session.close()


def enqueue_task(task_type: str, payload: dict[str, Any] | None = None) -> str:
    key = (task_type or "").strip()
    if not key:
        raise ValueError("task_type 不能为空")

    task_id = uuid4().hex
    session = SessionLocal()
    try:
        task = Task(
            id=task_id,
            task_type=key,
            status="queued",
            payload_json=_dumps_json(payload),
            result_json="{}",
            log_text="",
            error="",
        )
        session.add(task)
        session.commit()
        return task_id
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def _claim_queued_tasks(*, limit: int) -> list[str]:
    limit = max(1, int(limit))
    claimed: list[str] = []

    session = SessionLocal()
    try:
        candidates = list(
            session.scalars(
                select(Task.id)
                .where(Task.status == "queued")
                .order_by(Task.created_at.asc(), Task.id.asc())
                .limit(max(limit * 3, limit))
            )
        )

        for task_id in candidates:
            now = _now_utc()
            result = session.execute(
                update(Task)
                .where(Task.id == task_id, Task.status == "queued")
                .values(status="running", started_at=now, updated_at=now)
            )
            if result.rowcount != 1:
                session.rollback()
                continue
            session.commit()
            claimed.append(task_id)
            append_task_log(task_id, "任务已启动。")
            if len(claimed) >= limit:
                break
    except Exception:
        session.rollback()
    finally:
        session.close()

    return claimed


def _execute_task(task_id: str) -> None:
    session = SessionLocal()
    try:
        task = session.get(Task, task_id)
        if task is None:
            return

        task_type = task.task_type
        payload = _loads_json(task.payload_json)

        with _TASK_HANDLER_LOCK:
            handler = _TASK_HANDLERS.get(task_type)

        if handler is None:
            task.status = "failed"
            task.error = f"unknown task_type: {task_type}"
            task.finished_at = _now_utc()
            task.updated_at = _now_utc()
            session.commit()
            append_task_log(task_id, f"任务失败: {task.error}")
            return

        append_task_log(task_id, f"执行任务类型: {task_type}")

        token = _CURRENT_TASK_ID.set(task_id)
        try:
            result = handler(payload, lambda msg: append_task_log(task_id, msg)) or {}
            session.expire_all()
            task = session.get(Task, task_id)
            if task is None:
                return
            task.result_json = _dumps_json(result)
            task.error = ""
            task.finished_at = _now_utc()
            task.updated_at = _now_utc()
            if task.status in {"cancel_requested", "cancelled"}:
                task.status = "cancelled"
                session.commit()
                append_task_log(task_id, "任务已取消。")
            else:
                task.status = "completed"
                session.commit()
                append_task_log(task_id, "任务已完成。")
        except Exception as exc:  # pragma: no cover
            session.rollback()
            task = session.get(Task, task_id)
            if task is None:
                return
            if task.status in {"cancel_requested", "cancelled"}:
                task.status = "cancelled"
                task.error = ""
            else:
                task.status = "failed"
                task.error = f"{exc.__class__.__name__}: {exc}"
            task.finished_at = _now_utc()
            task.updated_at = _now_utc()
            session.commit()
            if task.status == "cancelled":
                append_task_log(task_id, "任务已取消。")
            else:
                append_task_log(task_id, f"任务失败: {task.error}")
        finally:
            _CURRENT_TASK_ID.reset(token)
    except Exception:
        session.rollback()
    finally:
        session.close()


def _task_to_snapshot(task: Task, *, from_line: int = 0) -> dict[str, Any]:
    logs = [line for line in (task.log_text or "").splitlines() if line]
    safe_from = max(0, int(from_line))

    return {
        "job_id": task.id,
        "task_id": task.id,
        "task_type": task.task_type,
        "status": task.status,
        "payload": _loads_json(task.payload_json),
        "result": _loads_json(task.result_json),
        "logs": logs[safe_from:],
        "next_line": len(logs),
        "error": task.error or None,
        "created_at": task.created_at,
        "started_at": task.started_at,
        "finished_at": task.finished_at,
        "updated_at": task.updated_at,
    }


def get_task_snapshot(task_id: str, from_line: int = 0) -> dict[str, Any] | None:
    session = SessionLocal()
    try:
        task = session.get(Task, task_id)
        if task is None:
            return None
        return _task_to_snapshot(task, from_line=from_line)
    finally:
        session.close()


def replace_task_payload(task_id: str, payload: dict[str, Any]) -> dict[str, Any] | None:
    session = SessionLocal()
    try:
        task = session.get(Task, task_id)
        if task is None:
            return None
        if task.status in _TERMINAL_STATUSES:
            return _task_to_snapshot(task, from_line=0)
        task.payload_json = _dumps_json(payload)
        task.updated_at = _now_utc()
        session.commit()
        session.refresh(task)
        return _task_to_snapshot(task, from_line=0)
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def pause_task(task_id: str) -> dict[str, Any] | None:
    session = SessionLocal()
    try:
        task = session.get(Task, task_id)
        if task is None:
            return None
        if task.status in _TERMINAL_STATUSES or task.status == "cancel_requested":
            return _task_to_snapshot(task, from_line=0)
        if task.status != "paused":
            task.status = "paused"
            task.updated_at = _now_utc()
            session.commit()
            session.refresh(task)
        return _task_to_snapshot(task, from_line=0)
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def resume_task(task_id: str) -> dict[str, Any] | None:
    session = SessionLocal()
    try:
        task = session.get(Task, task_id)
        if task is None:
            return None
        if task.status in _TERMINAL_STATUSES or task.status == "cancel_requested":
            return _task_to_snapshot(task, from_line=0)
        if task.status == "paused":
            task.status = "running" if task.started_at is not None else "queued"
            task.updated_at = _now_utc()
            session.commit()
            session.refresh(task)
        return _task_to_snapshot(task, from_line=0)
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def cancel_task(task_id: str) -> dict[str, Any] | None:
    session = SessionLocal()
    try:
        task = session.get(Task, task_id)
        if task is None:
            return None
        if task.status in _TERMINAL_STATUSES:
            return _task_to_snapshot(task, from_line=0)
        if task.status == "queued" or (task.status == "paused" and task.started_at is None):
            task.status = "cancelled"
            task.error = ""
            task.finished_at = _now_utc()
            task.updated_at = _now_utc()
            session.commit()
            session.refresh(task)
            return _task_to_snapshot(task, from_line=0)
        task.status = "cancel_requested"
        task.updated_at = _now_utc()
        session.commit()
        session.refresh(task)
        return _task_to_snapshot(task, from_line=0)
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def is_task_cancel_requested(task_id: str | None) -> bool:
    if not task_id:
        return False
    session = SessionLocal()
    try:
        status = session.scalar(select(Task.status).where(Task.id == task_id))
        return str(status or "") in {"cancel_requested", "cancelled"}
    finally:
        session.close()


def wait_if_task_paused(
    task_id: str | None,
    *,
    logger: Callable[[str], None] | None = None,
    poll_interval_seconds: float | None = None,
) -> bool:
    if not task_id:
        return False
    interval = max(0.1, float(poll_interval_seconds or settings.task_poll_interval_seconds or 0.5))
    notified = False
    while True:
        session = SessionLocal()
        try:
            status = str(session.scalar(select(Task.status).where(Task.id == task_id)) or "")
        finally:
            session.close()

        if status == "paused":
            if not notified and logger is not None:
                logger("任务已暂停，等待继续或停止指令...")
                notified = True
            time.sleep(interval)
            continue
        if notified and logger is not None:
            logger("任务继续执行。")
        return status in {"cancel_requested", "cancelled"}


def list_task_snapshots(
    *,
    task_type: str | None = None,
    status: str | None = None,
    offset: int = 0,
    limit: int = 50,
) -> tuple[list[dict[str, Any]], int]:
    safe_offset = max(0, int(offset))
    safe_limit = max(1, min(int(limit), 200))

    session = SessionLocal()
    try:
        stmt = select(Task)
        count_stmt = select(func.count()).select_from(Task)

        if task_type:
            stmt = stmt.where(Task.task_type == task_type)
            count_stmt = count_stmt.where(Task.task_type == task_type)

        if status:
            stmt = stmt.where(Task.status == status)
            count_stmt = count_stmt.where(Task.status == status)

        total = int(session.scalar(count_stmt) or 0)
        items = session.scalars(
            stmt.order_by(Task.created_at.desc(), Task.id.desc()).offset(safe_offset).limit(safe_limit)
        ).all()

        snapshots = [
            {
                "task_id": task.id,
                "task_type": task.task_type,
                "status": task.status,
                "created_at": task.created_at,
                "started_at": task.started_at,
                "finished_at": task.finished_at,
                "updated_at": task.updated_at,
            }
            for task in items
        ]
        return snapshots, total
    finally:
        session.close()


def start_worker() -> None:
    global _WORKER
    with _WORKER_LOCK:
        if _WORKER is not None:
            return
        _WORKER = TaskWorker(
            max_workers=settings.task_worker_concurrency,
            poll_interval_seconds=settings.task_poll_interval_seconds,
        )
        _WORKER.start()


def stop_worker() -> None:
    global _WORKER
    with _WORKER_LOCK:
        if _WORKER is None:
            return
        worker = _WORKER
        _WORKER = None
        worker.stop()


def wait_for_idle(timeout_seconds: float = 30.0) -> bool:
    deadline = time.time() + max(0.1, timeout_seconds)
    while time.time() < deadline:
        session = SessionLocal()
        try:
            running = session.scalar(
                select(func.count()).where(Task.status.in_(["queued", "running", "paused", "cancel_requested"]))
            ) or 0
            if int(running) == 0:
                return True
        finally:
            session.close()
        time.sleep(0.2)
    return False
