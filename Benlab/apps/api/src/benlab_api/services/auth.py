from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from benlab_api.models import Member
from benlab_api.services.logs import record_log
from benlab_api.services.security import hash_password, verify_password


def authenticate_member(db: Session, *, username: str, password: str) -> Member | None:
    member = db.scalar(select(Member).where(Member.username == username))
    if not member or not verify_password(password, member.password_hash):
        return None
    return member


def validate_registration_input(name: str, username: str, password: str) -> str | None:
    if not name or not username or not password:
        return "请填写姓名、用户名和密码"
    return None


def username_exists(db: Session, *, username: str) -> bool:
    return db.scalar(select(Member).where(Member.username == username)) is not None


def create_member(
    db: Session,
    *,
    name: str,
    username: str,
    password: str,
    contact: str,
) -> Member:
    member = Member(
        name=name,
        username=username,
        password_hash=hash_password(password),
        contact=contact,
    )
    db.add(member)
    db.flush()
    record_log(db, user_id=member.id, action_type="注册", details=f"{member.username} completed signup")
    db.commit()
    return member

