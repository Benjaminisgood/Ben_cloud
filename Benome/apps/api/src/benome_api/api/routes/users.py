from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ...models import User
from ...schemas.user import PasswordChangeRequest, UserCreateRequest, UserOut, UserUpdateRequest
from ...services.errors import ServiceError
from ...services.users import (
    change_current_user_password,
    create_user_by_admin,
    delete_user_by_admin,
    get_user_detail_by_admin,
    list_all_users_for_admin,
    toggle_user_status_by_admin,
    update_current_user_profile,
    update_user_by_admin,
)
from ..deps import get_current_user, get_current_admin, get_db

router = APIRouter(tags=["users"])


def _to_user_out(user: User) -> UserOut:
    return UserOut(
        id=user.id,
        username=user.username,
        full_name=user.full_name,
        phone=user.phone,
        role=user.role,
        is_active=user.is_active,
        created_at=user.created_at,
        updated_at=user.updated_at,
    )


@router.get("/users/me", response_model=UserOut)
def get_current_user_api(
    current_user: User = Depends(get_current_user),
):
    """获取当前登录用户的信息"""
    return _to_user_out(current_user)


@router.put("/users/me", response_model=UserOut)
def update_current_user_api(
    payload: UserUpdateRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """更新当前登录用户的信息"""
    try:
        user = update_current_user_profile(
            db,
            current_user=current_user,
            full_name=payload.full_name,
            phone=payload.phone,
        )
    except ServiceError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.detail) from None
    return _to_user_out(user)


@router.post("/users/me/change-password")
def change_password_api(
    payload: PasswordChangeRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """修改当前登录用户的密码"""
    try:
        change_current_user_password(
            db,
            current_user=current_user,
            old_password=payload.old_password,
            new_password=payload.new_password,
            confirm_password=payload.confirm_password,
        )
    except ServiceError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.detail) from None
    return {"message": "密码修改成功"}


@router.get("/admin/users", response_model=list[UserOut])
def list_all_users(
    admin: User = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    """管理员获取所有用户列表"""
    try:
        users = list_all_users_for_admin(db, admin=admin)
    except ServiceError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.detail) from None
    return [_to_user_out(user) for user in users]


@router.post("/admin/users", response_model=UserOut)
def create_user_api(
    payload: UserCreateRequest,
    admin: User = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    """管理员创建新用户"""
    try:
        user = create_user_by_admin(
            db,
            admin=admin,
            username=payload.username,
            password=payload.password,
            full_name=payload.full_name,
            phone=payload.phone,
            role=payload.role,
        )
    except ServiceError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.detail) from None
    return _to_user_out(user)


@router.get("/admin/users/{user_id}", response_model=UserOut)
def get_user_api(
    user_id: int,
    admin: User = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    """管理员获取单个用户详情"""
    try:
        user = get_user_detail_by_admin(db, admin=admin, user_id=user_id)
    except ServiceError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.detail) from None
    return _to_user_out(user)


@router.put("/admin/users/{user_id}", response_model=UserOut)
def update_user_api(
    user_id: int,
    payload: UserUpdateRequest,
    admin: User = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    """管理员更新用户信息"""
    try:
        user = update_user_by_admin(
            db,
            admin=admin,
            user_id=user_id,
            full_name=payload.full_name,
            phone=payload.phone,
        )
    except ServiceError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.detail) from None
    return _to_user_out(user)


@router.patch("/admin/users/{user_id}/toggle-status", response_model=UserOut)
def toggle_user_status_api(
    user_id: int,
    admin: User = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    """管理员切换用户激活状态"""
    try:
        user = toggle_user_status_by_admin(db, admin=admin, user_id=user_id)
    except ServiceError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.detail) from None
    return _to_user_out(user)


@router.delete("/admin/users/{user_id}")
def delete_user_api(
    user_id: int,
    admin: User = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    """管理员删除用户"""
    try:
        delete_user_by_admin(db, admin=admin, user_id=user_id)
    except ServiceError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.detail) from None
    return {"message": "用户已删除"}
