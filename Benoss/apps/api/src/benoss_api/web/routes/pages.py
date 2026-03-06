from __future__ import annotations

from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.orm import Session

from ...db.session import get_db
from ...services.page_views import (
    admin_page_context,
    board_page_context,
    can_access_admin,
    echoes_page_context,
    home_page_context,
    notice_page_context,
)
from ..deps import get_session_user
from ..flash import pop_flash
from ..templating import render_template
from ..utils import login_redirect

router = APIRouter(tags=["pages"])


@router.get("/", response_class=HTMLResponse)
def home(request: Request, db: Session = Depends(get_db)):
    user = get_session_user(request, db)
    if not user:
        return login_redirect(request)

    context = home_page_context(user)
    context["flash_messages"] = pop_flash(request)
    return render_template(request, "home.html", context)


@router.get("/board", response_class=HTMLResponse)
def board(request: Request, db: Session = Depends(get_db)):
    user = get_session_user(request, db)
    if not user:
        return login_redirect(request, next_path="/board")

    context = board_page_context(user)
    context["flash_messages"] = pop_flash(request)
    return render_template(request, "board.html", context)


@router.get("/echoes", response_class=HTMLResponse)
def echoes(request: Request, db: Session = Depends(get_db)):
    user = get_session_user(request, db)
    if not user:
        return login_redirect(request, next_path="/echoes")

    context = echoes_page_context(user)
    context["flash_messages"] = pop_flash(request)
    return render_template(request, "echoes.html", context)


@router.get("/notice", response_class=HTMLResponse)
def notice(request: Request, db: Session = Depends(get_db)):
    user = get_session_user(request, db)
    if not user:
        return login_redirect(request, next_path="/notice")

    context = notice_page_context(user)
    context["flash_messages"] = pop_flash(request)
    return render_template(request, "notice.html", context)


@router.get("/admin", response_class=HTMLResponse)
def admin(request: Request, db: Session = Depends(get_db)):
    user = get_session_user(request, db)
    if not user:
        return login_redirect(request, next_path="/admin")
    if not can_access_admin(user):
        return RedirectResponse("/", status_code=302)

    context = admin_page_context(user)
    context["flash_messages"] = pop_flash(request)
    return render_template(request, "admin.html", context)
