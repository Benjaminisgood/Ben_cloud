from __future__ import annotations

from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlmodel import Session

from benusy_api.core.config import get_settings
from benusy_api.models import Role

from ..deps import get_db, get_session_user
from ..templating import render_template

router = APIRouter(tags=["pages"])
settings = get_settings()


@router.get("/", response_class=HTMLResponse)
def index(request: Request):
    return render_template(request, "index.html", {"title": settings.APP_NAME})


@router.get("/dashboard", response_class=HTMLResponse)
def dashboard_page(request: Request, db: Session = Depends(get_db)):
    user = get_session_user(request, db)
    if not user:
        return RedirectResponse("/login", status_code=302)
    return render_template(request, "dashboard.html", {"title": "仪表盘", "current_user": user})


@router.get("/tasks", response_class=HTMLResponse)
def tasks_page(request: Request):
    return render_template(request, "tasks.html", {"title": "任务"})


@router.get("/assignments", response_class=HTMLResponse)
def assignments_page(request: Request):
    return render_template(request, "assignments.html", {"title": "分配"})


@router.get("/profile", response_class=HTMLResponse)
def profile_page(request: Request):
    return render_template(request, "profile.html", {"title": "个人资料"})


@router.get("/admin", response_class=RedirectResponse, include_in_schema=False)
def admin_redirect() -> RedirectResponse:
    return RedirectResponse(url="/admin/dashboard", status_code=302)


@router.get("/admin/dashboard", response_class=HTMLResponse)
def admin_dashboard_page(request: Request, db: Session = Depends(get_db)):
    user = get_session_user(request, db)
    if not user or user.role != Role.admin:
        return RedirectResponse("/login", status_code=302)
    return render_template(request, "admin_dashboard.html", {"title": "管理员控制台", "current_user": user})


@router.get("/admin/users", response_class=HTMLResponse)
def admin_users_page(request: Request):
    return render_template(request, "admin_users.html", {"title": "达人审核中心"})


@router.get("/admin/settlements", response_class=HTMLResponse)
def admin_settlements_page(request: Request):
    return render_template(request, "admin_settlements.html", {"title": "收益结款中心"})


@router.get("/admin/reviews", response_class=HTMLResponse)
def admin_reviews_page(request: Request):
    return render_template(request, "admin_reviews.html", {"title": "作业审核中心"})


@router.get("/admin/tasks", response_class=HTMLResponse)
def admin_tasks_page(request: Request):
    return render_template(request, "admin_tasks.html", {"title": "任务运营中心"})
