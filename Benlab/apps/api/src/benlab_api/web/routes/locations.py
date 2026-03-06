from __future__ import annotations

from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session

from benlab_api.core.constants import LOCATION_STATUS_CHOICES, LOCATION_USAGE_TAG_CHOICES
from benlab_api.db.session import get_db
from benlab_api.models import Attachment, Location, Member
from benlab_api.repositories.locations_repo import (
    get_location,
    get_location_for_detail,
    list_all_items,
    list_items_by_ids as list_location_items_by_ids,
    list_location_form_options,
    list_locations_for_overview,
    list_members_by_ids as list_location_members_by_ids,
)
from benlab_api.services.event_views import build_event_summary
from benlab_api.services.forms import parse_id_list, parse_tags
from benlab_api.services.location_views import (
    build_affiliation_summary,
    build_location_detail_refs,
    build_location_item_stats,
    collect_location_detail_refs,
    filter_available_items,
    resolve_location_item_ids,
    to_float,
)
from benlab_api.services.logs import record_log
from benlab_api.services.uploads import remove_upload, save_upload
from benlab_api.web.deps import get_current_user
from benlab_api.web.flash import flash
from benlab_api.web.templating import render_template
from benlab_api.web.utils import login_redirect
from benlab_api.web.viewmodels import base_template_context


router = APIRouter(tags=["locations"])


@router.get("/locations", name="locations_list")
def list_locations(
    request: Request,
    db: Session = Depends(get_db),
    current_user: Member | None = Depends(get_current_user),
):
    if not current_user:
        return login_redirect(request)

    locations = list_locations_for_overview(db)
    context = base_template_context()
    context.update(
        {
            "locations": locations,
            "status_choices": LOCATION_STATUS_CHOICES,
            "usage_tag_choices": LOCATION_USAGE_TAG_CHOICES,
        }
    )
    return render_template(request, "locations.html", context, current_user=current_user)


@router.get("/locations/add", name="add_location")
def add_location_page(
    request: Request,
    db: Session = Depends(get_db),
    current_user: Member | None = Depends(get_current_user),
):
    if not current_user:
        return login_redirect(request)

    members, locations = list_location_form_options(db)
    context = base_template_context()
    context.update(
        {
            "location": None,
            "members": members,
            "parents": locations,
            "location_status_choices": LOCATION_STATUS_CHOICES,
            "selected_usage_tags": [],
            "editable_detail_refs": [],
        }
    )
    return render_template(request, "location_form.html", context, current_user=current_user)


@router.post("/locations/add", name="add_location_post")
async def add_location_submit(
    request: Request,
    db: Session = Depends(get_db),
    current_user: Member | None = Depends(get_current_user),
):
    if not current_user:
        return login_redirect(request)

    form = await request.form()
    name = str(form.get("name", "")).strip()
    if not name:
        flash(request, "空间名称不能为空", "danger")
        return RedirectResponse(url=request.url_for("add_location"), status_code=303)

    parent_selected = str(form.get("parent_location_select", "")).strip()
    parent_id = parent_selected or str(form.get("parent_id", "")).strip()
    usage_tags = parse_tags(form.getlist("usage_tags"))
    detail_refs_input = collect_location_detail_refs(form)
    detail_refs_raw = build_location_detail_refs(
        str(form.get("detail_refs", "")).strip(),
        usage_tags,
        detail_refs_input,
    )

    location = Location(
        name=name,
        parent_id=int(parent_id) if parent_id.isdigit() else None,
        status=str(form.get("status", LOCATION_STATUS_CHOICES[0])).strip() or LOCATION_STATUS_CHOICES[0],
        latitude=to_float(form.get("latitude")),
        longitude=to_float(form.get("longitude")),
        coordinate_source=str(form.get("coordinate_source", "")).strip(),
        notes=str(form.get("notes", "")).strip(),
        is_public=bool(form.get("is_public")),
        detail_link=str(form.get("detail_link", "")).strip(),
        detail_refs_raw=detail_refs_raw,
    )

    member_ids = parse_id_list(form.getlist("member_ids")) or parse_id_list(form.getlist("responsible_ids"))
    if member_ids:
        location.responsible_members = list_location_members_by_ids(db, member_ids=member_ids)

    files = [file for file in form.getlist("attachments") if getattr(file, "filename", "")]
    for file in files:
        location.attachments.append(Attachment(filename=save_upload(file), location=location))

    external_urls_raw = str(form.get("external_attachment_urls", "")).strip()
    if external_urls_raw:
        for line in external_urls_raw.splitlines():
            ref = line.strip()
            if ref:
                location.attachments.append(Attachment(filename=ref, location=location))

    db.add(location)
    db.flush()
    record_log(db, user_id=current_user.id, location_id=location.id, action_type="新增位置", details=location.name)
    db.commit()

    flash(request, "空间已创建", "success")
    return RedirectResponse(url=request.url_for("view_location", loc_id=location.id), status_code=303)


@router.get("/locations/{loc_id}/edit", name="edit_location")
def edit_location_page(
    loc_id: int,
    request: Request,
    db: Session = Depends(get_db),
    current_user: Member | None = Depends(get_current_user),
):
    if not current_user:
        return login_redirect(request)

    location = get_location(db, location_id=loc_id)
    if not location:
        raise HTTPException(status_code=404, detail="Location not found")

    members, locations = list_location_form_options(db, exclude_location_id=loc_id)
    context = base_template_context()
    context.update(
        {
            "location": location,
            "members": members,
            "parents": locations,
            "location_status_choices": LOCATION_STATUS_CHOICES,
            "selected_usage_tags": location.usage_tags,
            "editable_detail_refs": location.detail_refs_without_usage_tags,
        }
    )
    return render_template(request, "location_form.html", context, current_user=current_user)


@router.post("/locations/{loc_id}/edit", name="edit_location_post")
async def edit_location_submit(
    loc_id: int,
    request: Request,
    db: Session = Depends(get_db),
    current_user: Member | None = Depends(get_current_user),
):
    if not current_user:
        return login_redirect(request)

    location = get_location(db, location_id=loc_id)
    if not location:
        raise HTTPException(status_code=404, detail="Location not found")

    form = await request.form()
    name = str(form.get("name", "")).strip()
    if not name:
        flash(request, "空间名称不能为空", "danger")
        return RedirectResponse(url=request.url_for("edit_location", loc_id=location.id), status_code=303)

    parent_selected = str(form.get("parent_location_select", "")).strip()
    parent_id = parent_selected or str(form.get("parent_id", "")).strip()
    if parent_id.isdigit() and int(parent_id) == location.id:
        flash(request, "父级空间不能是自己", "danger")
        return RedirectResponse(url=request.url_for("edit_location", loc_id=location.id), status_code=303)

    location.name = name
    location.parent_id = int(parent_id) if parent_id.isdigit() else None
    location.status = str(form.get("status", LOCATION_STATUS_CHOICES[0])).strip() or LOCATION_STATUS_CHOICES[0]
    location.latitude = to_float(form.get("latitude"))
    location.longitude = to_float(form.get("longitude"))
    location.coordinate_source = str(form.get("coordinate_source", "")).strip()
    location.notes = str(form.get("notes", "")).strip()
    location.is_public = bool(form.get("is_public"))
    location.detail_link = str(form.get("detail_link", "")).strip()

    usage_tags = parse_tags(form.getlist("usage_tags"))
    detail_refs_input = collect_location_detail_refs(form)
    location.detail_refs_raw = build_location_detail_refs(
        str(form.get("detail_refs", "")).strip(),
        usage_tags,
        detail_refs_input,
    )
    location.last_modified = datetime.now(UTC).replace(tzinfo=None)

    member_ids = parse_id_list(form.getlist("member_ids")) or parse_id_list(form.getlist("responsible_ids"))
    location.responsible_members = list_location_members_by_ids(db, member_ids=member_ids) if member_ids else []

    remove_ids = parse_id_list(form.getlist("remove_attachment_ids"))
    if remove_ids:
        for attachment in list(location.attachments):
            if attachment.id in remove_ids:
                remove_upload(attachment.filename)
                db.delete(attachment)

    files = [file for file in form.getlist("attachments") if getattr(file, "filename", "")]
    for file in files:
        location.attachments.append(Attachment(filename=save_upload(file), location=location))

    external_urls_raw = str(form.get("external_attachment_urls", "")).strip()
    if external_urls_raw:
        existing_refs = {attachment.filename for attachment in location.attachments}
        for line in external_urls_raw.splitlines():
            ref = line.strip()
            if ref and ref not in existing_refs:
                location.attachments.append(Attachment(filename=ref, location=location))

    record_log(db, user_id=current_user.id, location_id=location.id, action_type="编辑位置", details=location.name)
    db.commit()

    flash(request, "空间已更新", "success")
    return RedirectResponse(url=request.url_for("view_location", loc_id=location.id), status_code=303)


@router.post("/locations/{loc_id}/delete", name="delete_location")
def delete_location(
    loc_id: int,
    request: Request,
    db: Session = Depends(get_db),
    current_user: Member | None = Depends(get_current_user),
):
    if not current_user:
        return login_redirect(request)

    location = get_location(db, location_id=loc_id)
    if not location:
        raise HTTPException(status_code=404, detail="Location not found")

    loc_name = location.name
    for attachment in list(location.attachments):
        remove_upload(attachment.filename)

    record_log(db, user_id=current_user.id, location_id=location.id, action_type="删除位置", details=loc_name)
    db.delete(location)
    db.commit()

    flash(request, f"已删除空间：{loc_name}", "info")
    return RedirectResponse(url=request.url_for("locations_list"), status_code=303)


@router.get("/locations/{loc_id}", name="view_location")
def view_location(
    loc_id: int,
    request: Request,
    db: Session = Depends(get_db),
    current_user: Member | None = Depends(get_current_user),
):
    if not current_user:
        return login_redirect(request)

    location = get_location_for_detail(db, location_id=loc_id)
    if not location:
        raise HTTPException(status_code=404, detail="Location not found")

    available_items = filter_available_items(list_all_items(db), list(location.items))
    event_summary = build_event_summary(list(location.events), now=datetime.now(UTC).replace(tzinfo=None))
    status_stats, category_stats, feature_stats = build_location_item_stats(list(location.items))
    affiliation_summary = build_affiliation_summary(list(location.responsible_members))

    context = base_template_context()
    context.update(
        {
            "location": location,
            "items": list(location.items),
            "available_items": available_items,
            "event_summary": event_summary,
            "status_stats": status_stats,
            "category_stats": category_stats,
            "feature_stats": feature_stats,
            "affiliation_summary": affiliation_summary,
            "affiliation_total": len(affiliation_summary),
        }
    )
    return render_template(request, "location_detail.html", context, current_user=current_user)


@router.post("/locations/{loc_id}/items/manage", name="manage_location_items")
async def manage_location_items(
    loc_id: int,
    request: Request,
    db: Session = Depends(get_db),
    current_user: Member | None = Depends(get_current_user),
):
    if not current_user:
        return login_redirect(request)

    location = get_location(db, location_id=loc_id)
    if not location:
        raise HTTPException(status_code=404, detail="Location not found")

    form = await request.form()
    action = str(form.get("action", "add")).strip().lower()
    item_ids = resolve_location_item_ids(form, action=action)
    if not item_ids:
        flash(request, "请选择物品", "warning")
        return RedirectResponse(url=request.url_for("view_location", loc_id=location.id), status_code=303)

    items = list_location_items_by_ids(db, item_ids=item_ids)
    if action == "remove":
        to_remove = {item.id for item in items}
        location.items = [item for item in location.items if item.id not in to_remove]
        action_label = "移除"
    else:
        existing_ids = {item.id for item in location.items}
        for item in items:
            if item.id not in existing_ids:
                location.items.append(item)
        action_label = "添加"

    location.last_modified = datetime.now(UTC).replace(tzinfo=None)
    record_log(
        db,
        user_id=current_user.id,
        location_id=location.id,
        action_type=f"位置物品{action_label}",
        details=f"count={len(items)}",
    )
    db.commit()

    flash(request, f"已{action_label} {len(items)} 个物品", "success")
    return RedirectResponse(url=request.url_for("view_location", loc_id=location.id), status_code=303)
