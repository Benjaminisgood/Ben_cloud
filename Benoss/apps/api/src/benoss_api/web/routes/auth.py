from __future__ import annotations

from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.orm import Session

from ...db.session import get_db
from ...services.auth import authenticate_user, create_user, username_exists, validate_registration_input
from ...services.page_views import login_page_context, register_page_context
from ..deps import get_session_user, login_session, logout_session
from ..flash import flash, pop_flash
from ..templating import render_template

router = APIRouter(tags=["auth"])


@router.get("/login", response_class=HTMLResponse)
def login_page(request: Request, next: str = "", db: Session = Depends(get_db)):
    user = get_session_user(request, db)
    if user:
        return RedirectResponse("/", status_code=302)
    context = login_page_context(next)
    context["flash_messages"] = pop_flash(request)
    return render_template(request, "login.html", context)


@router.post("/login", response_class=HTMLResponse)
async def login_post(request: Request, db: Session = Depends(get_db)):
    form = await request.form()
    username = (str(form.get("username") or "")).strip()
    password = str(form.get("password") or "")
    next_url = str(form.get("next") or "").strip() or "/"

    user = authenticate_user(db, username=username, password=password)
    if user:
        login_session(request, user)
        return RedirectResponse(next_url, status_code=302)

    flash(request, "用户名或密码错误", "error")
    return RedirectResponse(f"/login?next={next_url}", status_code=302)


@router.get("/register", response_class=HTMLResponse)
def register_page(request: Request, db: Session = Depends(get_db)):
    user = get_session_user(request, db)
    if user:
        return RedirectResponse("/", status_code=302)
    context = register_page_context()
    context["flash_messages"] = pop_flash(request)
    return render_template(request, "register.html", context)


@router.post("/register", response_class=HTMLResponse)
async def register_post(request: Request, db: Session = Depends(get_db)):
    form = await request.form()
    username = (str(form.get("username") or "")).strip()
    password = str(form.get("password") or "")
    password_confirm = str(form.get("password_confirm") or "")

    error = validate_registration_input(username, password, password_confirm)
    if not error and username_exists(db, username=username):
        error = "用户名已存在"

    if error:
        flash(request, error, "error")
        return RedirectResponse("/register", status_code=302)

    create_user(db, username=username, password=password)
    flash(request, "注册成功，请登录", "success")
    return RedirectResponse("/login", status_code=302)


@router.get("/logout")
def logout(request: Request):
    logout_session(request)
    return RedirectResponse("/login", status_code=302)
