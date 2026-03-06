from __future__ import annotations

from sqlalchemy import inspect, select
from sqlalchemy.orm import Session

from benlab_api.core.config import get_settings
from benlab_api.db.base import Base
from benlab_api.db.migrations import ensure_migration_state
from benlab_api.db.session import engine
from benlab_api.models import Member
from benlab_api.services.security import hash_password


def init_db() -> None:
    if get_settings().DB_BOOTSTRAP_CREATE_ALL:
        Base.metadata.create_all(bind=engine)
    ensure_migration_state()
    with Session(engine) as db:
        seed_admin(db)


def _members_table_exists(db: Session) -> bool:
    bound = db.get_bind()
    if bound is None:
        return False
    return "members" in inspect(bound).get_table_names()


def seed_admin(db: Session) -> None:
    if not _members_table_exists(db):
        return
    settings = get_settings()
    username = (settings.ADMIN_USERNAME or "").strip()
    password = settings.ADMIN_PASSWORD
    if not username or not password:
        return

    admin = db.scalar(select(Member).where(Member.username == username))
    if admin:
        return
    member = Member(
        name="管理员",
        username=username,
        password_hash=hash_password(password),
        contact="",
        notes="请尽快修改默认密码",
    )
    db.add(member)
    db.commit()
