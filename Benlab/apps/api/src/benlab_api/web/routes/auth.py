from __future__ import annotations

from fastapi import APIRouter, Depends, Request
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session

from benlab_api.db.session import get_db
from benlab_api.models import Member
from benlab_api.services.auth import (
    authenticate_member,
    create_member,
    username_exists,
    validate_registration_input,
)
from benlab_api.web.deps import get_current_user
from benlab_api.web.flash import flash
from benlab_api.web.templating import render_template
from benlab_api.web.viewmodels import base_template_context


router = APIRouter(tags=["auth"])


@router.get("/login", name="login")
def login_page(request: Request, current_user: Member | None = Depends(get_current_user)):
    if current_user:
        return RedirectResponse(url=request.url_for("index"), status_code=303)
    context = base_template_context()
    context.update({"next_url": request.query_params.get("next", "")})
    return render_template(request, "login.html", context, current_user=current_user)


@router.post("/login", name="login_post")
async def login_submit(request: Request, db: Session = Depends(get_db)):
    form = await request.form()
    username = str(form.get("username", "")).strip()
    password = str(form.get("password", ""))
    next_url = str(form.get("next", "")).strip()

    member = authenticate_member(db, username=username, password=password)
    if not member:
        flash(request, "用户名或密码错误", "danger")
        return RedirectResponse(url=request.url_for("login"), status_code=303)

    request.session["user_id"] = member.id
    flash(request, f"欢迎回来，{member.name or member.username}", "success")

    if next_url.startswith("/"):
        return RedirectResponse(url=next_url, status_code=303)
    return RedirectResponse(url=request.url_for("index"), status_code=303)


@router.get("/register", name="register")
def register_page(request: Request, current_user: Member | None = Depends(get_current_user)):
    if current_user:
        return RedirectResponse(url=request.url_for("index"), status_code=303)
    context = base_template_context()
    context.update({"next_url": request.query_params.get("next", "")})
    return render_template(request, "register.html", context, current_user=current_user)


@router.post("/register", name="register_post")
async def register_submit(request: Request, db: Session = Depends(get_db)):
    form = await request.form()
    name = str(form.get("name", "")).strip()
    username = str(form.get("username", "")).strip()
    password = str(form.get("password", "")).strip()
    contact = str(form.get("contact", "")).strip()
    next_url = str(form.get("next", "")).strip()

    input_error = validate_registration_input(name, username, password)
    if input_error:
        flash(request, input_error, "danger")
        return RedirectResponse(url=request.url_for("register"), status_code=303)

    if username_exists(db, username=username):
        flash(request, "用户名已存在", "danger")
        return RedirectResponse(url=request.url_for("register"), status_code=303)

    member = create_member(
        db,
        name=name,
        username=username,
        password=password,
        contact=contact,
    )

    request.session["user_id"] = member.id
    flash(request, "注册成功", "success")
    if next_url.startswith("/"):
        return RedirectResponse(url=next_url, status_code=303)
    return RedirectResponse(url=request.url_for("index"), status_code=303)


@router.get("/logout", name="logout")
def logout(request: Request):
    request.session.clear()
    flash(request, "已退出登录", "info")
    return RedirectResponse(url=request.url_for("login"), status_code=303)
