from __future__ import annotations

from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session

from benlab_api.core.constants import ITEM_FEATURE_CHOICES, ITEM_STATUS_CHOICES
from benlab_api.db.session import get_db
from benlab_api.models import Attachment, Item, Member
from benlab_api.repositories.items_repo import (
    get_item,
    get_item_for_detail,
    list_categorized_items,
    list_item_form_options,
    list_items_by_ids,
    list_items_for_overview,
    list_locations_by_ids,
    list_members_by_ids,
    list_non_empty_categories,
    list_uncategorized_items,
)
from benlab_api.services.event_views import build_event_summary
from benlab_api.services.forms import parse_id_list
from benlab_api.services.item_views import (
    build_category_payload,
    collect_item_detail_refs,
    parse_external_attachment_refs,
    parse_item_value,
    parse_purchase_date,
    resolve_item_features,
    sorted_non_empty_categories,
)
from benlab_api.services.logs import record_log
from benlab_api.services.uploads import remove_upload, save_upload
from benlab_api.web.deps import get_current_user
from benlab_api.web.flash import flash
from benlab_api.web.templating import render_template
from benlab_api.web.utils import login_redirect
from benlab_api.web.viewmodels import base_template_context


router = APIRouter(tags=["items"])


@router.get("/items", name="items")
def list_items(
    request: Request,
    db: Session = Depends(get_db),
    current_user: Member | None = Depends(get_current_user),
):
    if not current_user:
        return login_redirect(request)

    items = list_items_for_overview(db)
    categories = sorted_non_empty_categories(items)
    context = base_template_context()
    context.update(
        {
            "items": items,
            "item_status_choices": ITEM_STATUS_CHOICES,
            "feature_choices": ITEM_FEATURE_CHOICES,
            "categories": categories,
        }
    )
    return render_template(request, "items.html", context, current_user=current_user)


@router.get("/items/add", name="add_item")
def add_item_page(
    request: Request,
    loc_id: int | None = None,
    db: Session = Depends(get_db),
    current_user: Member | None = Depends(get_current_user),
):
    if not current_user:
        return login_redirect(request)

    members, locations = list_item_form_options(db)
    categories = list_non_empty_categories(db)
    context = base_template_context()
    context.update(
        {
            "item": None,
            "members": members,
            "locations": locations,
            "item_status_choices": ITEM_STATUS_CHOICES,
            "feature_choices": ITEM_FEATURE_CHOICES,
            "default_loc_id": loc_id,
            "categories": categories,
        }
    )
    return render_template(request, "item_form.html", context, current_user=current_user)


@router.post("/items/add", name="add_item_post")
async def add_item_submit(
    request: Request,
    db: Session = Depends(get_db),
    current_user: Member | None = Depends(get_current_user),
):
    if not current_user:
        return login_redirect(request)
    form = await request.form()

    name = str(form.get("name", "")).strip()
    if not name:
        flash(request, "物品名称不能为空", "danger")
        return RedirectResponse(url=request.url_for("add_item"), status_code=303)

    member_ids = parse_id_list(form.getlist("member_ids")) or parse_id_list(form.getlist("responsible_ids"))
    location_ids = parse_id_list(form.getlist("location_ids"))

    item = Item(
        name=name,
        category=str(form.get("category", "")).strip(),
        status=str(form.get("status", ITEM_STATUS_CHOICES[0])).strip() or ITEM_STATUS_CHOICES[0],
        features=resolve_item_features(form),
        quantity_desc=str(form.get("quantity_desc", "")).strip(),
        notes=str(form.get("notes", "")).strip(),
        purchase_link=str(form.get("purchase_link", "")).strip(),
        detail_refs=collect_item_detail_refs(form) or str(form.get("detail_refs", "")).strip(),
        purchase_date=parse_purchase_date(str(form.get("purchase_date", "")).strip()),
    )
    item.value = parse_item_value(str(form.get("value", "")).strip())

    if member_ids:
        item.responsible_members = list_members_by_ids(db, member_ids=member_ids)
    if location_ids:
        item.locations = list_locations_by_ids(db, location_ids=location_ids)

    files = [file for file in form.getlist("attachments") if getattr(file, "filename", "")]
    for file in files:
        item.attachments.append(Attachment(filename=save_upload(file), item=item))

    for ref in parse_external_attachment_refs(str(form.get("external_attachment_urls", "")).strip()):
        item.attachments.append(Attachment(filename=ref, item=item))

    db.add(item)
    db.flush()
    record_log(db, user_id=current_user.id, item_id=item.id, action_type="新增物品", details=item.name)
    db.commit()

    flash(request, "物品已创建", "success")
    return RedirectResponse(url=request.url_for("item_detail", item_id=item.id), status_code=303)


@router.get("/items/{item_id}/edit", name="edit_item")
def edit_item_page(
    item_id: int,
    request: Request,
    db: Session = Depends(get_db),
    current_user: Member | None = Depends(get_current_user),
):
    if not current_user:
        return login_redirect(request)

    item = get_item(db, item_id=item_id)
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")

    members, locations = list_item_form_options(db)
    categories = list_non_empty_categories(db)
    context = base_template_context()
    context.update(
        {
            "item": item,
            "members": members,
            "locations": locations,
            "item_status_choices": ITEM_STATUS_CHOICES,
            "feature_choices": ITEM_FEATURE_CHOICES,
            "default_loc_id": None,
            "categories": categories,
        }
    )
    return render_template(request, "item_form.html", context, current_user=current_user)


@router.post("/items/{item_id}/edit", name="edit_item_post")
async def edit_item_submit(
    item_id: int,
    request: Request,
    db: Session = Depends(get_db),
    current_user: Member | None = Depends(get_current_user),
):
    if not current_user:
        return login_redirect(request)

    item = get_item(db, item_id=item_id)
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")

    form = await request.form()
    name = str(form.get("name", "")).strip()
    if not name:
        flash(request, "物品名称不能为空", "danger")
        return RedirectResponse(url=request.url_for("edit_item", item_id=item.id), status_code=303)

    item.name = name
    item.category = str(form.get("category", "")).strip()
    item.status = str(form.get("status", ITEM_STATUS_CHOICES[0])).strip() or ITEM_STATUS_CHOICES[0]
    item.features = resolve_item_features(form)
    item.quantity_desc = str(form.get("quantity_desc", "")).strip()
    item.notes = str(form.get("notes", "")).strip()
    item.purchase_link = str(form.get("purchase_link", "")).strip()
    item.detail_refs = collect_item_detail_refs(form) or str(form.get("detail_refs", "")).strip()
    item.purchase_date = parse_purchase_date(str(form.get("purchase_date", "")).strip())
    item.value = parse_item_value(str(form.get("value", "")).strip())

    member_ids = parse_id_list(form.getlist("member_ids")) or parse_id_list(form.getlist("responsible_ids"))
    location_ids = parse_id_list(form.getlist("location_ids"))
    item.responsible_members = list_members_by_ids(db, member_ids=member_ids) if member_ids else []
    item.locations = list_locations_by_ids(db, location_ids=location_ids) if location_ids else []

    remove_ids = parse_id_list(form.getlist("remove_attachment_ids"))
    if remove_ids:
        for attachment in list(item.attachments):
            if attachment.id in remove_ids:
                remove_upload(attachment.filename)
                db.delete(attachment)

    files = [file for file in form.getlist("attachments") if getattr(file, "filename", "")]
    for file in files:
        item.attachments.append(Attachment(filename=save_upload(file), item=item))

    existing_refs = {attachment.filename for attachment in item.attachments}
    for ref in parse_external_attachment_refs(str(form.get("external_attachment_urls", "")).strip()):
        if ref not in existing_refs:
            item.attachments.append(Attachment(filename=ref, item=item))

    item.last_modified = datetime.now(UTC).replace(tzinfo=None)
    record_log(db, user_id=current_user.id, item_id=item.id, action_type="编辑物品", details=item.name)
    db.commit()

    flash(request, "物品已更新", "success")
    return RedirectResponse(url=request.url_for("item_detail", item_id=item.id), status_code=303)


@router.post("/items/{item_id}/delete", name="delete_item")
def delete_item(
    item_id: int,
    request: Request,
    db: Session = Depends(get_db),
    current_user: Member | None = Depends(get_current_user),
):
    if not current_user:
        return login_redirect(request)

    item = get_item(db, item_id=item_id)
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")

    item_name = item.name
    for attachment in list(item.attachments):
        remove_upload(attachment.filename)

    record_log(db, user_id=current_user.id, item_id=item.id, action_type="删除物品", details=item_name)
    db.delete(item)
    db.commit()

    flash(request, f"已删除物品：{item_name}", "info")
    return RedirectResponse(url=request.url_for("items"), status_code=303)


@router.get("/items/{item_id:int}", name="item_detail")
def item_detail(
    item_id: int,
    request: Request,
    db: Session = Depends(get_db),
    current_user: Member | None = Depends(get_current_user),
):
    if not current_user:
        return login_redirect(request)

    item = get_item_for_detail(db, item_id=item_id)
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")

    categories, category_payload = build_category_payload(list_categorized_items(db))
    uncategorized_items = list_uncategorized_items(db)
    event_summary = build_event_summary(list(item.events), now=datetime.now(UTC).replace(tzinfo=None))

    context = base_template_context()
    context.update(
        {
            "item": item,
            "categories": categories,
            "category_payload": category_payload,
            "uncategorized_items": uncategorized_items,
            "detail_refs": item.detail_refs,
            "event_summary": event_summary,
            "interest_summary": [],
            "interest_total": 0,
        }
    )
    return render_template(request, "item_detail.html", context, current_user=current_user)


@router.post("/items/manage-category", name="manage_item_category")
async def manage_item_category(
    request: Request,
    db: Session = Depends(get_db),
    current_user: Member | None = Depends(get_current_user),
):
    if not current_user:
        return login_redirect(request)

    form = await request.form()
    target_ids = parse_id_list(form.getlist("item_ids"))
    category = str(form.get("category", "")).strip()
    if not target_ids:
        flash(request, "请选择要更新的物品", "warning")
        return RedirectResponse(url=request.url_for("items"), status_code=303)

    items = list_items_by_ids(db, item_ids=target_ids)
    for item in items:
        item.category = category
        item.last_modified = datetime.now(UTC).replace(tzinfo=None)

    record_log(
        db,
        user_id=current_user.id,
        action_type="批量设置分类",
        details=f"{len(items)} items => {category}",
    )
    db.commit()

    flash(request, f"已更新 {len(items)} 个物品分类", "success")
    return RedirectResponse(url=request.url_for("items"), status_code=303)
