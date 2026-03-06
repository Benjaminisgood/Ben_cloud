"""项目日志与报错记录服务。"""
from __future__ import annotations

from typing import Optional

from sqlalchemy.orm import Session

from ..models.project_log import ProjectLog
from ..repositories import (
    count_project_logs,
    create_project_log,
    list_project_logs,
    trim_project_logs,
)

_MAX_LOG_ENTRIES = 500   # 每个项目最多保留的日志条数


def add_log(
    db: Session,
    project_id: str,
    message: str,
    level: str = "INFO",
    source: str = "system",
) -> None:
    """向数据库写入一条日志记录，并自动裁剪超出上限的旧记录。"""
    create_project_log(
        db,
        project_id=project_id,
        message=message,
        level=level,
        source=source,
    )
    trim_project_logs(db, project_id=project_id, max_entries=_MAX_LOG_ENTRIES)


def get_logs(
    db: Session,
    project_id: str,
    level: Optional[str] = None,
    limit: int = 100,
    offset: int = 0,
) -> list[ProjectLog]:
    """查询指定项目的日志，可按级别过滤，按时间倒序返回。"""
    return list_project_logs(
        db,
        project_id=project_id,
        level=level,
        limit=limit,
        offset=offset,
    )


def count_logs(
    db: Session,
    project_id: str,
    level: Optional[str] = None,
) -> int:
    """统计日志条数。"""
    return count_project_logs(db, project_id=project_id, level=level)
