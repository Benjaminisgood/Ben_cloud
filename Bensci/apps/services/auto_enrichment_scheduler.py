from __future__ import annotations

from threading import Event, Lock, Thread

from apps.core.config import settings
from apps.models.schemas import EnrichmentFillRequest
from apps.services.enrichment_jobs import (
    cancel_active_auto_fill_jobs,
    create_auto_fill_empty_enrichment_job,
    has_pending_auto_fill_job,
)
from apps.services.runtime_settings import load_auto_enrichment_enabled, save_auto_enrichment_enabled


class AutoEnrichmentScheduler:
    def __init__(self) -> None:
        self._stop_event = Event()
        self._thread: Thread | None = None

    def start(self) -> None:
        if self._thread is not None and self._thread.is_alive():
            return
        self._stop_event.clear()
        self._thread = Thread(target=self._run_loop, daemon=True, name="auto-enrichment-loop")
        self._thread.start()

    def stop(self) -> None:
        self._stop_event.set()
        if self._thread is not None:
            self._thread.join(timeout=5)

    def _build_payload(self) -> EnrichmentFillRequest:
        limit = max(1, min(int(settings.auto_enrichment_limit), 1000))
        workers = max(1, min(int(settings.auto_enrichment_workers), 16))
        return EnrichmentFillRequest(limit=limit, workers=workers)

    def _run_loop(self) -> None:
        while not self._stop_event.is_set():
            try:
                if not has_pending_auto_fill_job():
                    create_auto_fill_empty_enrichment_job(self._build_payload())
            except Exception:
                # 后台守护任务容错
                pass

            interval = max(10, int(settings.auto_enrichment_interval_seconds))
            self._stop_event.wait(interval)


_SCHEDULER: AutoEnrichmentScheduler | None = None
_LOCK = Lock()
_AUTO_ENRICHMENT_RUNTIME_ENABLED = bool(settings.auto_enrichment_enabled)
_RUNTIME_STATE_LOADED = False


def _ensure_runtime_state_loaded_unlocked() -> None:
    global _AUTO_ENRICHMENT_RUNTIME_ENABLED, _RUNTIME_STATE_LOADED
    if _RUNTIME_STATE_LOADED:
        return
    _AUTO_ENRICHMENT_RUNTIME_ENABLED = load_auto_enrichment_enabled(default=_AUTO_ENRICHMENT_RUNTIME_ENABLED)
    _RUNTIME_STATE_LOADED = True


def _start_scheduler_unlocked() -> None:
    global _SCHEDULER
    if _SCHEDULER is None:
        _SCHEDULER = AutoEnrichmentScheduler()
    _SCHEDULER.start()


def _stop_scheduler_unlocked() -> None:
    global _SCHEDULER
    if _SCHEDULER is None:
        return
    scheduler = _SCHEDULER
    _SCHEDULER = None
    scheduler.stop()


def get_auto_enrichment_enabled() -> bool:
    with _LOCK:
        _ensure_runtime_state_loaded_unlocked()
        return _AUTO_ENRICHMENT_RUNTIME_ENABLED


def set_auto_enrichment_enabled(enabled: bool) -> bool:
    global _AUTO_ENRICHMENT_RUNTIME_ENABLED
    with _LOCK:
        _ensure_runtime_state_loaded_unlocked()
        _AUTO_ENRICHMENT_RUNTIME_ENABLED = bool(enabled)
        save_auto_enrichment_enabled(_AUTO_ENRICHMENT_RUNTIME_ENABLED)
        if _AUTO_ENRICHMENT_RUNTIME_ENABLED:
            _start_scheduler_unlocked()
        else:
            _stop_scheduler_unlocked()
            cancel_active_auto_fill_jobs()
        return _AUTO_ENRICHMENT_RUNTIME_ENABLED


def start_auto_enrichment_scheduler() -> None:
    with _LOCK:
        _ensure_runtime_state_loaded_unlocked()
        if not _AUTO_ENRICHMENT_RUNTIME_ENABLED:
            return
        _start_scheduler_unlocked()


def stop_auto_enrichment_scheduler() -> None:
    with _LOCK:
        _stop_scheduler_unlocked()
