from __future__ import annotations

from datetime import datetime
from typing import Iterable

from sqlalchemy.orm import Session

from ..models.user_project_access import UserProjectAccess


def list_project_ids_for_user(db: Session, user_id: int) -> list[str]:
    rows = (
        db.query(UserProjectAccess.project_id)
        .filter_by(user_id=user_id)
        .order_by(UserProjectAccess.project_id.asc())
        .all()
    )
    return [row[0] for row in rows]


def list_access_rows_for_users(db: Session, user_ids: Iterable[int]) -> list[UserProjectAccess]:
    normalized_ids = sorted({int(user_id) for user_id in user_ids})
    if not normalized_ids:
        return []
    return (
        db.query(UserProjectAccess)
        .filter(UserProjectAccess.user_id.in_(normalized_ids))
        .all()
    )


def replace_user_project_access(
    db: Session,
    *,
    user_id: int,
    project_ids: Iterable[str],
    granted_by: str | None,
) -> list[UserProjectAccess]:
    normalized_project_ids = sorted({project_id.strip().lower() for project_id in project_ids if project_id.strip()})

    db.query(UserProjectAccess).filter_by(user_id=user_id).delete(synchronize_session=False)

    now = datetime.utcnow()
    rows = [
        UserProjectAccess(
            user_id=user_id,
            project_id=project_id,
            granted_by=granted_by,
            created_at=now,
        )
        for project_id in normalized_project_ids
    ]
    if rows:
        db.add_all(rows)
    db.commit()
    for row in rows:
        db.refresh(row)
    return rows
