from __future__ import annotations

from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlmodel import Session, select

from benusy_api.core.security import verify_password
from benusy_api.models import User

from ..deps import get_db, get_session_user, login_session, logout_session
from ..templating import render_template

router = APIRouter(tags=["auth"])


@router.get("/login", response_class=HTMLResponse)
def login_page(request: Request, db: Session = Depends(get_db)):
    if get_session_user(request, db):
        return RedirectResponse("/", status_code=302)
    return render_template(request, "login.html", {"title": "登录"})


@router.post("/login", response_class=HTMLResponse)
async def login_post(request: Request, db: Session = Depends(get_db)):
    form = await request.form()
    username = (str(form.get("username") or "")).strip()
    password = str(form.get("password") or "")

    user = db.exec(
        select(User).where(
            (User.email == username) | (User.phone == username) | (User.username == username)
        )
    ).first()
    if not user or not verify_password(password, user.hashed_password):
        return RedirectResponse("/login?error=invalid", status_code=302)
    if not user.is_active:
        return RedirectResponse("/login?error=inactive", status_code=302)

    login_session(request, user)
    return RedirectResponse("/", status_code=302)


@router.get("/auth/register", response_class=HTMLResponse)
def register_page(request: Request):
    return render_template(request, "register.html", {"title": "注册"})


@router.get("/logout")
def logout(request: Request):
    logout_session(request)
    return RedirectResponse("/login", status_code=302)
