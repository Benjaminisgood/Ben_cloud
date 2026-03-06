from __future__ import annotations

from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import RedirectResponse, Response
from sqlalchemy.orm import Session

from benlab_api.core.constants import EVENT_VISIBILITY_CHOICES
from benlab_api.db.session import get_db
from benlab_api.models import Attachment, Event, EventParticipant, Item, Location, Member
from benlab_api.repositories.events_repo import (
    get_event,
    get_event_for_detail,
    get_event_for_edit,
    get_event_with_participant_links,
    list_form_options,
    list_items_by_ids,
    list_locations_by_ids,
    list_valid_member_ids,
    list_visible_events,
)
from benlab_api.services.events import (
    format_datetime_local,
    generate_event_share_token,
    generate_poster_png,
    parse_datetime_local,
    verify_event_share_token,
)
from benlab_api.services.event_views import parse_feedback_entries, split_events_by_time
from benlab_api.services.forms import parse_id_list
from benlab_api.services.logs import record_log
from benlab_api.services.uploads import remove_upload, save_upload
from benlab_api.web.deps import get_current_user
from benlab_api.web.flash import flash
from benlab_api.web.template_helpers import default_form_state
from benlab_api.web.templating import render_template
from benlab_api.web.utils import login_redirect
from benlab_api.web.viewmodels import base_template_context


router = APIRouter(tags=["events"])


def _ensure_owner_participant(event: Event) -> None:
    for link in event.participant_links:
        if link.member_id == event.owner_id:
            link.role = "owner"
            link.status = "confirmed"
            return
    event.participant_links.append(
        EventParticipant(member_id=event.owner_id, role="owner", status="confirmed")
    )


def _is_event_visible(event: Event, user: Member | None) -> bool:
    return event.can_view(user)


def _forbidden_context(back_url: str, description: str) -> dict:
    context = base_template_context()
    context.update({"back_url": back_url, "description": description})
    return context


@router.get("/events", name="events_overview")
def events_overview(
    request: Request,
    db: Session = Depends(get_db),
    current_user: Member | None = Depends(get_current_user),
):
    if not current_user:
        return login_redirect(request)

    events = list_visible_events(db, member_id=current_user.id)
    now = datetime.now(UTC).replace(tzinfo=None)
    upcoming_events, past_events = split_events_by_time(events, now=now)

    context = base_template_context()
    context.update(
        {
            "events": events,
            "upcoming_events": upcoming_events,
            "past_events": past_events,
            "visibility_choices": EVENT_VISIBILITY_CHOICES,
            "now": now,
        }
    )
    return render_template(request, "events.html", context, current_user=current_user)


@router.get("/events/add", name="add_event")
def add_event_page(
    request: Request,
    db: Session = Depends(get_db),
    current_user: Member | None = Depends(get_current_user),
):
    if not current_user:
        return login_redirect(request)

    members, items, locations = list_form_options(db)

    context = base_template_context()
    context.update(
        {
            "event": None,
            "members": members,
            "items": items,
            "locations": locations,
            "visibility_choices": EVENT_VISIBILITY_CHOICES,
            "format_datetime_local": format_datetime_local,
            "form_state": default_form_state(),
            "preview_limit": 4,
        }
    )
    return render_template(request, "event_form.html", context, current_user=current_user)


@router.post("/events/add", name="add_event_post")
async def add_event_submit(
    request: Request,
    db: Session = Depends(get_db),
    current_user: Member | None = Depends(get_current_user),
):
    if not current_user:
        return login_redirect(request)

    form = await request.form()
    title = str(form.get("title", "")).strip()
    if not title:
        flash(request, "事项标题不能为空", "danger")
        return RedirectResponse(url=request.url_for("add_event"), status_code=303)

    visibility = str(form.get("visibility", "personal")).strip()
    if visibility not in EVENT_VISIBILITY_CHOICES:
        visibility = "personal"

    event = Event(
        title=title,
        description=str(form.get("description", "")).strip(),
        visibility=visibility,
        owner_id=current_user.id,
        start_time=parse_datetime_local(str(form.get("start_time", "")).strip()),
        end_time=parse_datetime_local(str(form.get("end_time", "")).strip()),
        detail_link=str(form.get("detail_link", "")).strip(),
        allow_participant_edit=bool(form.get("allow_participant_edit")),
    )

    participant_ids = parse_id_list(form.getlist("participant_ids"))
    if participant_ids:
        valid_ids = list_valid_member_ids(db, member_ids=participant_ids)
        for member_id in participant_ids:
            if member_id in valid_ids:
                event.participant_links.append(
                    EventParticipant(member_id=member_id, role="participant", status="confirmed")
                )
    _ensure_owner_participant(event)

    item_ids = parse_id_list(form.getlist("item_ids"))
    location_ids = parse_id_list(form.getlist("location_ids"))
    if item_ids:
        event.items = list_items_by_ids(db, item_ids=item_ids)
    if location_ids:
        event.locations = list_locations_by_ids(db, location_ids=location_ids)

    files = [f for f in form.getlist("attachments") if getattr(f, "filename", "")]
    files.extend([f for f in form.getlist("event_attachments") if getattr(f, "filename", "")])
    for file in files:
        event.attachments.append(Attachment(filename=save_upload(file), event=event))

    external_urls_raw = str(form.get("external_event_attachment_urls", "")).strip()
    if external_urls_raw:
        for line in external_urls_raw.splitlines():
            ref = line.strip()
            if ref:
                event.attachments.append(Attachment(filename=ref, event=event))

    db.add(event)
    db.flush()
    record_log(db, user_id=current_user.id, event_id=event.id, action_type="新增事项", details=event.title)
    db.commit()

    flash(request, "事项已创建", "success")
    return RedirectResponse(url=request.url_for("event_detail", event_id=event.id), status_code=303)


@router.get("/events/{event_id}", name="event_detail")
def event_detail(
    event_id: int,
    request: Request,
    db: Session = Depends(get_db),
    current_user: Member | None = Depends(get_current_user),
):
    if not current_user:
        return login_redirect(request)

    event = get_event_for_detail(db, event_id=event_id)
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")

    if not _is_event_visible(event, current_user):
        return render_template(
            request,
            "error_403.html",
            _forbidden_context(str(request.url_for("events_overview")), "你没有权限查看该事项。"),
            current_user=current_user,
        )

    feedback_entries = parse_feedback_entries(event.feedback_log or "")

    share_token = generate_event_share_token(event.id)
    share_url = str(request.url_for("event_share_entry", event_id=event.id, token=share_token))

    context = base_template_context()
    context.update(
        {
            "event": event,
            "feedback_entries": feedback_entries,
            "share_url": share_url,
            "feedback_post_url": str(request.url_for("post_event_feedback", event_id=event.id)),
            "allow_join": event.can_join(current_user),
            "participant_links": list(event.participant_links),
            "linked_description": event.description or "",
            "missing_items": [],
            "missing_locations": [],
            "share_meta": {"detail_url": share_url},
            "format_datetime_local": format_datetime_local,
        }
    )
    return render_template(request, "event_detail.html", context, current_user=current_user)


@router.get("/events/{event_id}/poster.png", name="event_share_poster")
def event_share_poster(
    event_id: int,
    request: Request,
    db: Session = Depends(get_db),
    current_user: Member | None = Depends(get_current_user),
):
    if not current_user:
        return login_redirect(request)

    event = get_event(db, event_id=event_id)
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")
    if not event.can_view(current_user):
        return render_template(
            request,
            "error_403.html",
            _forbidden_context(str(request.url_for("events_overview")), "你没有权限查看该事项。"),
            current_user=current_user,
        )

    token = generate_event_share_token(event.id)
    detail_url = str(request.url_for("event_share_entry", event_id=event.id, token=token))
    png = generate_poster_png(event.title, detail_url)
    if not png:
        raise HTTPException(status_code=500, detail="Poster generation unavailable")
    return Response(content=png, media_type="image/png")


@router.get("/events/{event_id}/share/{token}", name="event_share_entry")
def event_share_entry(
    event_id: int,
    token: str,
    request: Request,
    db: Session = Depends(get_db),
    current_user: Member | None = Depends(get_current_user),
):
    verified_event_id = verify_event_share_token(token)
    if verified_event_id != event_id:
        raise HTTPException(status_code=403, detail="Invalid or expired share token")

    if not current_user:
        return RedirectResponse(url=f"{request.url_for('login')}?next={request.url.path}", status_code=303)

    event = get_event(db, event_id=event_id)
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")

    if event.visibility == "internal" and not event.is_participant(current_user) and event.owner_id != current_user.id:
        event.participant_links.append(
            EventParticipant(member_id=current_user.id, role="participant", status="confirmed")
        )
        record_log(db, user_id=current_user.id, event_id=event.id, action_type="扫码加入事项", details="share link")
        db.commit()

    return RedirectResponse(url=request.url_for("event_detail", event_id=event.id), status_code=303)


@router.post("/events/{event_id}/feedback", name="post_event_feedback")
async def post_event_feedback(
    event_id: int,
    request: Request,
    db: Session = Depends(get_db),
    current_user: Member | None = Depends(get_current_user),
):
    if not current_user:
        return login_redirect(request)

    event = get_event(db, event_id=event_id)
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")
    if not event.can_view(current_user):
        return render_template(
            request,
            "error_403.html",
            _forbidden_context(str(request.url_for("events_overview")), "你没有权限访问该分享事项。"),
            current_user=current_user,
        )

    form = await request.form()
    content = str(form.get("content", "")).strip()
    if content:
        line = f"{datetime.now(UTC).replace(tzinfo=None).isoformat()}|{current_user.username}|{content}"
        existing = event.feedback_log or ""
        event.feedback_log = f"{existing}\n{line}" if existing else line
        record_log(db, user_id=current_user.id, event_id=event.id, action_type="事项反馈", details=content[:120])
        db.commit()

    return RedirectResponse(url=request.url_for("event_detail", event_id=event.id), status_code=303)


@router.get("/events/{event_id}/edit", name="edit_event")
def edit_event_page(
    event_id: int,
    request: Request,
    db: Session = Depends(get_db),
    current_user: Member | None = Depends(get_current_user),
):
    if not current_user:
        return login_redirect(request)

    event = get_event_for_edit(db, event_id=event_id)
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")
    if not event.can_edit(current_user):
        return render_template(
            request,
            "error_403.html",
            _forbidden_context(str(request.url_for("event_detail", event_id=event.id)), "你没有权限编辑该事项。"),
            current_user=current_user,
        )

    members, items, locations = list_form_options(db)

    context = base_template_context()
    context.update(
        {
            "event": event,
            "members": members,
            "items": items,
            "locations": locations,
            "visibility_choices": EVENT_VISIBILITY_CHOICES,
            "format_datetime_local": format_datetime_local,
            "preview_limit": 4,
            "form_state": default_form_state(
                event,
                location_ids=[loc.id for loc in event.locations],
                item_ids=[item.id for item in event.items],
                participant_ids=[link.member_id for link in event.participant_links if link.member_id != event.owner_id],
            ),
        }
    )
    return render_template(request, "event_form.html", context, current_user=current_user)


@router.post("/events/{event_id}/edit", name="edit_event_post")
async def edit_event_submit(
    event_id: int,
    request: Request,
    db: Session = Depends(get_db),
    current_user: Member | None = Depends(get_current_user),
):
    if not current_user:
        return login_redirect(request)

    event = get_event_for_edit(db, event_id=event_id)
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")
    if not event.can_edit(current_user):
        return render_template(
            request,
            "error_403.html",
            _forbidden_context(str(request.url_for("event_detail", event_id=event.id)), "你没有权限编辑该事项。"),
            current_user=current_user,
        )

    form = await request.form()
    title = str(form.get("title", "")).strip()
    if not title:
        flash(request, "事项标题不能为空", "danger")
        return RedirectResponse(url=request.url_for("edit_event", event_id=event.id), status_code=303)

    visibility = str(form.get("visibility", "personal")).strip()
    if visibility not in EVENT_VISIBILITY_CHOICES:
        visibility = "personal"

    event.title = title
    event.description = str(form.get("description", "")).strip()
    event.visibility = visibility
    event.start_time = parse_datetime_local(str(form.get("start_time", "")).strip())
    event.end_time = parse_datetime_local(str(form.get("end_time", "")).strip())
    event.detail_link = str(form.get("detail_link", "")).strip()
    event.allow_participant_edit = bool(form.get("allow_participant_edit"))
    event.updated_at = datetime.now(UTC).replace(tzinfo=None)

    participant_ids = parse_id_list(form.getlist("participant_ids"))
    existing_map = {link.member_id: link for link in event.participant_links}
    keep_ids = set(participant_ids)
    keep_ids.add(event.owner_id)

    for link in list(event.participant_links):
        if link.member_id not in keep_ids:
            event.participant_links.remove(link)

    valid_ids = list_valid_member_ids(db, member_ids=participant_ids) if participant_ids else set()
    for member_id in participant_ids:
        if member_id not in valid_ids:
            continue
        if member_id not in existing_map:
            event.participant_links.append(
                EventParticipant(member_id=member_id, role="participant", status="confirmed")
            )
    _ensure_owner_participant(event)

    item_ids = parse_id_list(form.getlist("item_ids"))
    location_ids = parse_id_list(form.getlist("location_ids"))
    event.items = list_items_by_ids(db, item_ids=item_ids) if item_ids else []
    event.locations = list_locations_by_ids(db, location_ids=location_ids) if location_ids else []

    remove_ids = parse_id_list(form.getlist("remove_attachment_ids"))
    remove_ids.extend(parse_id_list(form.getlist("remove_event_attachment_ids")))
    if remove_ids:
        for att in list(event.attachments):
            if att.id in remove_ids:
                remove_upload(att.filename)
                db.delete(att)

    files = [f for f in form.getlist("attachments") if getattr(f, "filename", "")]
    files.extend([f for f in form.getlist("event_attachments") if getattr(f, "filename", "")])
    for file in files:
        event.attachments.append(Attachment(filename=save_upload(file), event=event))

    external_urls_raw = str(form.get("external_event_attachment_urls", "")).strip()
    if external_urls_raw:
        existing_refs = {att.filename for att in event.attachments}
        for line in external_urls_raw.splitlines():
            ref = line.strip()
            if ref and ref not in existing_refs:
                event.attachments.append(Attachment(filename=ref, event=event))

    record_log(db, user_id=current_user.id, event_id=event.id, action_type="编辑事项", details=event.title)
    db.commit()

    flash(request, "事项已更新", "success")
    return RedirectResponse(url=request.url_for("event_detail", event_id=event.id), status_code=303)


@router.post("/events/{event_id}/delete", name="delete_event")
def delete_event(
    event_id: int,
    request: Request,
    db: Session = Depends(get_db),
    current_user: Member | None = Depends(get_current_user),
):
    if not current_user:
        return login_redirect(request)

    event = get_event(db, event_id=event_id)
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")
    if not event.can_edit(current_user):
        return render_template(
            request,
            "error_403.html",
            _forbidden_context(str(request.url_for("event_detail", event_id=event.id)), "你没有权限删除该事项。"),
            current_user=current_user,
        )

    title = event.title
    for att in list(event.attachments):
        remove_upload(att.filename)
    record_log(db, user_id=current_user.id, event_id=event.id, action_type="删除事项", details=title)
    db.delete(event)
    db.commit()

    flash(request, f"已删除事项：{title}", "info")
    return RedirectResponse(url=request.url_for("events_overview"), status_code=303)


@router.post("/events/{event_id}/signup", name="signup_event")
def signup_event(
    event_id: int,
    request: Request,
    db: Session = Depends(get_db),
    current_user: Member | None = Depends(get_current_user),
):
    if not current_user:
        return login_redirect(request)

    event = get_event_with_participant_links(db, event_id=event_id)
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")

    if event.can_join(current_user):
        event.participant_links.append(
            EventParticipant(member_id=current_user.id, role="participant", status="confirmed")
        )
        record_log(db, user_id=current_user.id, event_id=event.id, action_type="报名事项", details=event.title)
        db.commit()
        flash(request, "报名成功", "success")
    else:
        flash(request, "当前不可报名该事项", "warning")

    return RedirectResponse(url=request.url_for("event_detail", event_id=event.id), status_code=303)


@router.post("/events/{event_id}/withdraw", name="withdraw_event")
def withdraw_event(
    event_id: int,
    request: Request,
    db: Session = Depends(get_db),
    current_user: Member | None = Depends(get_current_user),
):
    if not current_user:
        return login_redirect(request)

    event = get_event_with_participant_links(db, event_id=event_id)
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")

    if current_user.id == event.owner_id:
        flash(request, "创建者不能退出事项", "warning")
        return RedirectResponse(url=request.url_for("event_detail", event_id=event.id), status_code=303)

    for link in list(event.participant_links):
        if link.member_id == current_user.id:
            event.participant_links.remove(link)
            record_log(db, user_id=current_user.id, event_id=event.id, action_type="退出事项", details=event.title)
            db.commit()
            flash(request, "已退出事项", "info")
            break
    else:
        flash(request, "你不在该事项参与列表中", "warning")

    return RedirectResponse(url=request.url_for("event_detail", event_id=event.id), status_code=303)
