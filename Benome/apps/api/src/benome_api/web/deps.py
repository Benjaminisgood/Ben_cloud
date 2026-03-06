from __future__ import annotations

from fastapi import Depends, Request
from sqlalchemy.orm import Session

from benome_api.db.session import get_db as get_db_session
from benome_api.models import User


def get_db():
    yield from get_db_session()


def get_session_user(request: Request, db: Session = Depends(get_db)) -> User | None:
    # 优先从 session cookie 获取用户 ID（传统方式）
    user_id = request.session.get("user_id")
    
    # 如果 session 中没有，尝试从请求头获取（前端 localStorage 方式）
    if not user_id:
        user_id = request.headers.get("X-User-Id")
    
    if not user_id:
        return None
    
    try:
        user = db.get(User, int(user_id))
        if not user or not user.is_active:
            request.session.clear()
            return None
        return user
    except (ValueError, TypeError):
        return None


def login_session(request: Request, user: User) -> None:
    request.session["user_id"] = user.id
    request.session["username"] = user.username
    request.session["role"] = user.role


def logout_session(request: Request) -> None:
    request.session.clear()
