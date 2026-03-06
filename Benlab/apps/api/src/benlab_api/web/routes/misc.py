from __future__ import annotations

from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import FileResponse, JSONResponse, RedirectResponse
from sqlalchemy.orm import Session

from benlab_api.db.session import get_db
from benlab_api.models import Member
from benlab_api.repositories.misc_repo import (
    get_dashboard_counts,
    list_export_items,
    list_export_locations,
    list_export_logs,
    list_export_members,
    list_export_messages,
    list_graph_events,
    list_graph_items,
    list_graph_locations,
    list_graph_members,
    list_recent_logs,
    list_upcoming_events,
    search_items,
    search_locations,
)
from benlab_api.services.misc_views import (
    build_disabled_autofill_suggestion,
    build_graph_json,
    build_item_search_payload,
    build_location_search_payload,
    export_csv,
    to_items_export_rows,
    to_locations_export_rows,
    to_logs_export_rows,
    to_members_export_rows,
    to_messages_export_rows,
)
from benlab_api.services.uploads import abs_attachment_path
from benlab_api.web.deps import get_current_user
from benlab_api.web.templating import render_template
from benlab_api.web.utils import login_redirect
from benlab_api.web.viewmodels import base_template_context


router = APIRouter(tags=["misc"])


@router.get("/", name="index")
def index(
    request: Request,
    db: Session = Depends(get_db),
    current_user: Member | None = Depends(get_current_user),
):
    if not current_user:
        return login_redirect(request)

    counts = get_dashboard_counts(db)
    now = datetime.now(UTC).replace(tzinfo=None)
    upcoming_events = list_upcoming_events(db, now=now)
    recent_logs = list_recent_logs(db)

    graph_json = build_graph_json(
        current_user,
        members=list_graph_members(db, current_member_id=current_user.id),
        items=list_graph_items(db, current_member_id=current_user.id),
        locations=list_graph_locations(db, current_member_id=current_user.id),
        events=list_graph_events(db, current_member_id=current_user.id),
    )

    context = base_template_context()
    context.update(
        {
            **counts,
            "upcoming_events": upcoming_events,
            "recent_logs": recent_logs,
            "graph_json": graph_json,
        }
    )
    return render_template(request, "index.html", context, current_user=current_user)


@router.get("/pages/{page_id}", name="temporary_page")
def temporary_page(page_id: int):
    return JSONResponse({"ok": True, "page_id": page_id})


@router.get("/attachments/{filename:path}", name="uploaded_attachment")
def uploaded_attachment(filename: str):
    path = abs_attachment_path(filename)
    if not path.exists() or not path.is_file():
        raise HTTPException(status_code=404, detail="Attachment not found")
    return FileResponse(path)


@router.post("/api/uploads/oss/presign", name="create_direct_oss_upload")
async def create_direct_oss_upload():
    return JSONResponse({"ok": False, "error": "OSS direct upload is not enabled"}, status_code=400)


@router.post("/api/uploads/oss/verify", name="verify_direct_oss_upload")
async def verify_direct_oss_upload():
    return JSONResponse({"ok": False, "error": "OSS direct upload is not enabled"}, status_code=400)


@router.get("/api/items/search", name="search_items")
def search_items_endpoint(
    request: Request,
    q: str = Query(default="", max_length=120),
    db: Session = Depends(get_db),
    current_user: Member | None = Depends(get_current_user),
):
    if not current_user:
        return JSONResponse({"ok": False, "error": "unauthorized"}, status_code=401)
    items = search_items(db, keyword=q.strip())
    return build_item_search_payload(items, request)


@router.get("/api/locations/search", name="search_locations")
def search_locations_endpoint(
    request: Request,
    q: str = Query(default="", max_length=120),
    db: Session = Depends(get_db),
    current_user: Member | None = Depends(get_current_user),
):
    if not current_user:
        return JSONResponse({"ok": False, "error": "unauthorized"}, status_code=401)
    locations = search_locations(db, keyword=q.strip())
    return build_location_search_payload(locations, request)


@router.post("/api/forms/ai-autofill", name="ai_form_autofill")
async def ai_form_autofill(request: Request, current_user: Member | None = Depends(get_current_user)):
    if not current_user:
        return JSONResponse({"ok": False, "error": "unauthorized"}, status_code=401)
    form = await request.form()
    form_type = str(form.get("form_type", "item")).strip().lower()
    suggestion = build_disabled_autofill_suggestion(form_type)
    if suggestion is None:
        return JSONResponse({"ok": False, "error": "invalid form_type"}, status_code=400)

    return {
        "ok": True,
        "form_type": form_type,
        "model": "disabled",
        "suggestion": suggestion,
    }


@router.get("/export/{datatype}", name="export_data")
def export_data(
    datatype: str,
    request: Request,
    db: Session = Depends(get_db),
    current_user: Member | None = Depends(get_current_user),
):
    if not current_user:
        return login_redirect(request)

    token = datatype.strip().lower()
    if token == "items":
        return export_csv(to_items_export_rows(list_export_items(db)), "items.csv")

    if token == "members":
        return export_csv(to_members_export_rows(list_export_members(db)), "members.csv")

    if token == "locations":
        return export_csv(to_locations_export_rows(list_export_locations(db)), "locations.csv")

    if token == "logs":
        return export_csv(to_logs_export_rows(list_export_logs(db)), "logs.csv")

    if token == "messages":
        return export_csv(to_messages_export_rows(list_export_messages(db)), "messages.csv")

    raise HTTPException(status_code=404, detail="Unknown export datatype")
