from __future__ import annotations

from datetime import datetime

from benusy_api.core.security import create_access_token, get_password_hash
from benusy_api.models import (
    Assignment,
    AssignmentStatus,
    MetricSyncStatus,
    ReviewStatus,
    Role,
    Task,
    TaskStatus,
    User,
)
from sqlmodel import Session


def _seed_users_and_assignments() -> tuple[int, int]:
    from benusy_api.db.database import engine

    with Session(engine) as db:
        admin = User(
            email="admin@example.com",
            username="admin",
            hashed_password=get_password_hash("admin123"),
            role=Role.admin,
            review_status=ReviewStatus.approved,
            is_active=True,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )
        blogger = User(
            email="blogger@example.com",
            username="blogger",
            hashed_password=get_password_hash("blogger123"),
            role=Role.blogger,
            review_status=ReviewStatus.approved,
            is_active=True,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )
        db.add(admin)
        db.add(blogger)
        db.commit()
        db.refresh(admin)
        db.refresh(blogger)

        task = Task(
            title="有效任务",
            description="有效任务描述",
            platform="douyin",
            base_reward=100,
            instructions="执行要求",
            attachments=[],
            status=TaskStatus.published,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )
        db.add(task)
        db.commit()
        db.refresh(task)

        valid_assignment = Assignment(
            task_id=task.id or 0,
            user_id=blogger.id or 0,
            status=AssignmentStatus.accepted,
            metric_sync_status=MetricSyncStatus.normal,
            revenue=0.0,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )
        orphan_assignment = Assignment(
            task_id=999999,  # task 不存在，模拟历史脏数据
            user_id=blogger.id or 0,
            status=AssignmentStatus.in_review,
            metric_sync_status=MetricSyncStatus.manual_pending_review,
            revenue=0.0,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )
        db.add(valid_assignment)
        db.add(orphan_assignment)
        db.commit()

        return int(admin.id or 0), int(blogger.id or 0)


def test_assignments_endpoints_skip_orphan_records(client):
    admin_id, blogger_id = _seed_users_and_assignments()
    admin_token = create_access_token({"sub": str(admin_id), "role": Role.admin.value})
    blogger_token = create_access_token({"sub": str(blogger_id), "role": Role.blogger.value})

    admin_res = client.get(
        "/api/v1/admin/assignments",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert admin_res.status_code == 200
    admin_items = admin_res.json()
    assert len(admin_items) == 1
    assert admin_items[0]["task"]["title"] == "有效任务"

    blogger_res = client.get(
        "/api/v1/assignments/me",
        headers={"Authorization": f"Bearer {blogger_token}"},
    )
    assert blogger_res.status_code == 200
    blogger_items = blogger_res.json()
    assert len(blogger_items) == 1
    assert blogger_items[0]["task"]["title"] == "有效任务"
