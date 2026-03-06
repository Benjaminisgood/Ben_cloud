from __future__ import annotations

from urllib.parse import urlencode

from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.orm import Session

from ...db.session import get_db
from ...services import web_pages
from ...services.auth import (
    authenticate_user,
    create_user,
    get_user_by_username,
    validate_login_input,
    validate_register_input,
)
from ...services.metrics import inc_counter
from ..deps import login_session, logout_session, require_guest_or_redirect_home
from ..flash import flash, pop_flash
from ..templating import render_template

router = APIRouter(tags=["auth"])


@router.get("/login", response_class=HTMLResponse)
def login_page(request: Request, db: Session = Depends(get_db)):
    redirect = require_guest_or_redirect_home(request, db)
    if redirect:
        return redirect
    context_dto = web_pages.assemble_login_page_context(
        flash_messages=pop_flash(request),
        next_url=str(request.query_params.get("next") or ""),
    )
    return render_template(request, "login.html", context_dto.to_template_context())


@router.post("/login", response_class=HTMLResponse)
async def login_post(request: Request, db: Session = Depends(get_db)):
    form = await request.form()
    username = (str(form.get("username") or "")).strip()
    password = str(form.get("password") or "")
    next_url = web_pages.sanitize_next_url(str(form.get("next") or ""))

    error = validate_login_input(username, password)
    next_query = urlencode({"next": next_url})

    if error:
        inc_counter("benbot_login_failure_total")
        flash(request, error, "error")
        return RedirectResponse(f"/login?{next_query}", status_code=302)

    user = authenticate_user(db, username=username, password=password)
    if user:
        inc_counter("benbot_login_success_total")
        login_session(request, user)
        return RedirectResponse(next_url, status_code=302)

    inc_counter("benbot_login_failure_total")
    flash(request, "用户名或密码错误", "error")
    return RedirectResponse(f"/login?{next_query}", status_code=302)


@router.get("/logout")
def logout(request: Request):
    logout_session(request)
    return RedirectResponse("/login", status_code=302)


@router.get("/register", response_class=HTMLResponse)
def register_page(request: Request, db: Session = Depends(get_db)):
    redirect = require_guest_or_redirect_home(request, db)
    if redirect:
        return redirect
    context_dto = web_pages.assemble_register_page_context(
        flash_messages=pop_flash(request),
    )
    return render_template(request, "register.html", context_dto.to_template_context())


@router.post("/register", response_class=HTMLResponse)
async def register_post(request: Request, db: Session = Depends(get_db)):
    form = await request.form()
    username = (str(form.get("username") or "")).strip()
    password = str(form.get("password") or "")
    confirm_password = str(form.get("confirm_password") or "")

    error = validate_register_input(username, password, confirm_password)
    if error:
        flash(request, error, "error")
        return RedirectResponse("/register", status_code=302)

    # 检查用户名是否已存在
    existing_user = get_user_by_username(db, username=username)
    if existing_user:
        flash(request, "该用户名已被注册", "error")
        return RedirectResponse("/register", status_code=302)

    # 创建新用户
    create_user(db, username=username, password=password, role="user")

    flash(request, f"注册成功！欢迎 {username}", "success")
    return RedirectResponse("/login", status_code=302)
