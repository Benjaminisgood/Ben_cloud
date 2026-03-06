from __future__ import annotations

from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.orm import Session

from ...db.session import get_db
from ...schemas.web import SessionUserDTO
from ...services.web_pages import (
    assemble_dashboard_page_context,
    assemble_project_redirect_target,
)
from ..deps import require_session_user_or_redirect
from ..flash import pop_flash
from ..templating import render_template

router = APIRouter(tags=["pages"])


@router.get("/", response_class=HTMLResponse)
def index(request: Request, db: Session = Depends(get_db)):
    result = require_session_user_or_redirect(request, db)
    if isinstance(result, RedirectResponse):
        return result
    user: SessionUserDTO = result

    context_dto = assemble_dashboard_page_context(
        db=db,
        current_user=user,
        flash_messages=pop_flash(request),
    )
    return render_template(request, "index.html", context_dto.to_template_context())


@router.get("/goto/{project_id}")
def goto_project(project_id: str, request: Request, db: Session = Depends(get_db)):
    """Record click and redirect user to sub-project entry."""
    result = require_session_user_or_redirect(request, db)
    if isinstance(result, RedirectResponse):
        return result
    user: SessionUserDTO = result

    redirect_target = assemble_project_redirect_target(
        project_id=project_id,
        request=request,
        db=db,
        current_user=user,
    )
    if redirect_target is None:
        return RedirectResponse("/", status_code=302)
    return RedirectResponse(redirect_target.redirect_url, status_code=302)
