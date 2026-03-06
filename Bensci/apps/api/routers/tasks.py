from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import FileResponse

from apps.core.config import settings
from apps.models.schemas import TaskCreateRequest, TaskCreateResponse, TaskListResponse, TaskSnapshotResponse
from apps.services.task_queue import enqueue_task, get_task_snapshot, list_task_snapshots

router = APIRouter(prefix="/tasks", tags=["tasks"])


@router.post("", response_model=TaskCreateResponse)
def create_task(payload: TaskCreateRequest) -> TaskCreateResponse:
    try:
        task_id = enqueue_task(payload.task_type, dict(payload.payload or {}))
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    return TaskCreateResponse(task_id=task_id, status="queued")


@router.get("", response_model=TaskListResponse)
def list_tasks(
    task_type: str | None = Query(default=None),
    status: str | None = Query(default=None),
    offset: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1, le=200),
) -> TaskListResponse:
    items, total = list_task_snapshots(task_type=task_type, status=status, offset=offset, limit=limit)
    return TaskListResponse(total=total, items=items)


@router.get("/{task_id}", response_model=TaskSnapshotResponse)
def get_task(
    task_id: str,
    from_line: int = Query(default=0, ge=0),
) -> TaskSnapshotResponse:
    snapshot = get_task_snapshot(task_id=task_id, from_line=from_line)
    if snapshot is None:
        raise HTTPException(status_code=404, detail="任务不存在")
    return TaskSnapshotResponse.model_validate(snapshot)


@router.get("/{task_id}/download")
def download_task_artifact(task_id: str) -> FileResponse:
    snapshot = get_task_snapshot(task_id=task_id, from_line=0)
    if snapshot is None:
        raise HTTPException(status_code=404, detail="任务不存在")
    if snapshot.get("status") != "completed":
        raise HTTPException(status_code=409, detail="任务尚未完成")

    result = snapshot.get("result") or {}
    file_path = str(result.get("file_path") or "").strip()
    if not file_path:
        raise HTTPException(status_code=404, detail="任务无可下载文件")

    resolved = Path(file_path).resolve()
    export_root = settings.export_dir.resolve()

    try:
        resolved.relative_to(export_root)
    except Exception as exc:
        raise HTTPException(status_code=403, detail="非法下载路径") from exc

    if not resolved.exists() or not resolved.is_file():
        raise HTTPException(status_code=404, detail="文件不存在")

    return FileResponse(
        resolved,
        media_type="text/csv; charset=utf-8",
        filename=str(result.get("file_name") or resolved.name),
    )
