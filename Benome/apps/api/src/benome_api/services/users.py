from __future__ import annotations

from sqlalchemy.orm import Session

from ..models import User
from ..repositories.users_repo import create_user, get_user_by_id, get_user_by_username, list_users
from .errors import ServiceError

_ALLOWED_ROLES = {"admin", "customer"}


def _require_admin(admin: User) -> None:
    if admin.role != "admin":
        raise ServiceError("admin only", status_code=403)


def _normalize_role(role: str) -> str:
    normalized = role.strip().lower()
    if normalized not in _ALLOWED_ROLES:
        raise ServiceError("invalid role", status_code=400)
    return normalized


def _normalize_text(value: str | None) -> str:
    return value.strip() if value is not None else ""


def update_current_user_profile(
    db: Session,
    *,
    current_user: User,
    full_name: str | None,
    phone: str | None,
) -> User:
    if full_name is not None:
        current_user.full_name = _normalize_text(full_name)
    if phone is not None:
        current_user.phone = _normalize_text(phone)

    db.commit()
    db.refresh(current_user)
    return current_user


def change_current_user_password(
    db: Session,
    *,
    current_user: User,
    old_password: str,
    new_password: str,
    confirm_password: str,
) -> None:
    if not current_user.check_password(old_password):
        raise ServiceError("旧密码不正确", status_code=400)
    if len(new_password) < 6:
        raise ServiceError("新密码长度不能少于 6 位", status_code=400)
    if new_password != confirm_password:
        raise ServiceError("两次输入的新密码不一致", status_code=400)

    current_user.set_password(new_password)
    db.commit()


def list_all_users_for_admin(db: Session, *, admin: User) -> list[User]:
    _require_admin(admin)
    return list_users(db)


def create_user_by_admin(
    db: Session,
    *,
    admin: User,
    username: str,
    password: str,
    full_name: str | None,
    phone: str | None,
    role: str,
) -> User:
    _require_admin(admin)

    normalized_username = username.strip()
    if not normalized_username:
        raise ServiceError("用户名不能为空", status_code=400)
    if len(password) < 6:
        raise ServiceError("密码长度不能少于 6 位", status_code=400)
    if get_user_by_username(db, username=normalized_username):
        raise ServiceError("用户名已存在", status_code=400)

    user = create_user(
        db,
        username=normalized_username,
        password=password,
        role=_normalize_role(role),
        full_name=_normalize_text(full_name),
        phone=_normalize_text(phone),
    )
    db.commit()
    db.refresh(user)
    return user


def get_user_detail_by_admin(
    db: Session,
    *,
    admin: User,
    user_id: int,
) -> User:
    _require_admin(admin)
    user = get_user_by_id(db, user_id=user_id)
    if not user:
        raise ServiceError("用户不存在", status_code=404)
    return user


def update_user_by_admin(
    db: Session,
    *,
    admin: User,
    user_id: int,
    full_name: str | None,
    phone: str | None,
) -> User:
    _require_admin(admin)

    user = get_user_by_id(db, user_id=user_id)
    if not user:
        raise ServiceError("用户不存在", status_code=404)

    if full_name is not None:
        user.full_name = _normalize_text(full_name)
    if phone is not None:
        user.phone = _normalize_text(phone)

    db.commit()
    db.refresh(user)
    return user


def toggle_user_status_by_admin(
    db: Session,
    *,
    admin: User,
    user_id: int,
) -> User:
    _require_admin(admin)

    user = get_user_by_id(db, user_id=user_id)
    if not user:
        raise ServiceError("用户不存在", status_code=404)

    user.is_active = not user.is_active
    db.commit()
    db.refresh(user)
    return user


def delete_user_by_admin(
    db: Session,
    *,
    admin: User,
    user_id: int,
) -> None:
    _require_admin(admin)

    user = get_user_by_id(db, user_id=user_id)
    if not user:
        raise ServiceError("用户不存在", status_code=404)
    if user.id == admin.id:
        raise ServiceError("不能删除当前登录用户", status_code=400)

    db.delete(user)
    db.commit()
