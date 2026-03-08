
from __future__ import annotations

from fastapi import APIRouter, Query, Request
from fastapi.responses import HTMLResponse, RedirectResponse

from benhealth_api.core.config import get_settings
from benhealth_api.services.sso import verify_sso_token

from ..deps import get_session_user, login_session, logout_session
from ..templating import render_template

router = APIRouter(tags=["auth"])


@router.get("/login", response_class=HTMLResponse)
def login_page(request: Request, error: str | None = None, sso: str | None = None):
    current_user = get_session_user(request)
    if current_user:
        return RedirectResponse("/", status_code=303)
    message = None
    if error:
        message = "账号或密码错误，请重试。"
    if sso:
        message = "Benbot SSO 凭证无效或已过期，请重新登录。"
    return render_template(
        request,
        "login.html",
        {
            "title": "Benhealth 登录",
            "error_message": message,
        },
    )


@router.post("/login")
async def login(request: Request):
    form = await request.form()
    username = str(form.get("username", "")).strip()
    password = str(form.get("password", ""))
    next_url = str(form.get("next", "/")).strip() or "/"
    settings = get_settings()
    if username != settings.ADMIN_USERNAME or password != settings.ADMIN_PASSWORD:
        return RedirectResponse("/login?error=invalid", status_code=303)
    login_session(request, username=username, role="admin")
    return RedirectResponse(next_url, status_code=303)


@router.get("/logout")
def logout(request: Request):
    logout_session(request)
    return RedirectResponse("/login", status_code=303)


@router.get("/auth/sso")
def sso_callback(token: str = Query(...), request: Request = None):
    settings = get_settings()
    payload = verify_sso_token(settings.SSO_SECRET, token)
    if not payload:
        return RedirectResponse("/login?sso=invalid", status_code=303)

    username = str(payload.get("u", "")).strip()
    if not username:
        return RedirectResponse("/login?sso=invalid", status_code=303)

    role = "admin" if str(payload.get("r", "user")) == "admin" else "user"
    login_session(request, username=username, role=role)
    return RedirectResponse("/", status_code=303)
