from __future__ import annotations

from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import JSONResponse, RedirectResponse
from sqlalchemy.orm import Session

from benlab_api.db.session import get_db
from benlab_api.models import Member, Message
from benlab_api.repositories.members_repo import (
    get_member,
    get_member_for_profile,
    get_member_with_following,
    list_member_connection_candidates,
    list_member_connections,
    list_member_owned_events,
    list_member_participating_events,
    list_member_recent_messages,
    list_members_for_listing,
    list_profile_edit_options,
    list_profile_relation_targets,
    username_exists_excluding,
)
from benlab_api.services.admin_identity import is_admin_member
from benlab_api.services.member_connections import (
    MEMBER_CONNECTION_CLOSENESS,
    MEMBER_CONNECTION_TYPES,
    apply_member_connections,
    build_member_connection_view,
    parse_member_connections_form,
)
from benlab_api.services.logs import record_log
from benlab_api.services.member_profiles import (
    MEMBER_EVENT_REL_TYPES,
    MEMBER_GENDER_TYPES,
    MEMBER_ITEM_REL_TYPES,
    MEMBER_RELATION_TYPES,
    build_member_listing_cards,
    build_member_overview,
    build_profile_meta_from_form,
    build_profile_relation_sections,
    collect_profile_relation_ids,
    parse_profile_notes,
    serialize_profile_notes,
    split_owned_events,
)
from benlab_api.services.security import hash_password
from benlab_api.services.uploads import remove_upload, save_upload
from benlab_api.web.deps import get_current_user
from benlab_api.web.flash import flash
from benlab_api.web.templating import render_template
from benlab_api.web.utils import login_redirect
from benlab_api.web.viewmodels import base_template_context


router = APIRouter(tags=["members"])


def _forbidden_context(back_url: str, description: str) -> dict[str, object]:
    context = base_template_context()
    context.update({"back_url": back_url, "description": description})
    return context


def _can_manage_profile(current_user: Member | None, *, member_id: int) -> bool:
    if not current_user:
        return False
    return current_user.id == member_id or is_admin_member(current_user)


@router.get("/members", name="members_list")
def members_list(
    request: Request,
    db: Session = Depends(get_db),
    current_user: Member | None = Depends(get_current_user),
):
    if not current_user:
        return login_redirect(request)

    members = list_members_for_listing(db)
    viewer_is_admin = is_admin_member(current_user)
    followed_ids = {member.id for member in current_user.following}
    context = base_template_context()
    context.update(
        {
            "members": members,
            "member_cards": build_member_listing_cards(
                members,
                followed_ids=followed_ids,
                viewer_is_admin=viewer_is_admin,
            ),
            "directory_private_mode": viewer_is_admin,
            "followed_ids": followed_ids,
        }
    )
    return render_template(request, "members.html", context, current_user=current_user)


@router.post("/members/{member_id}/toggle_follow", name="toggle_follow")
def toggle_follow(
    member_id: int,
    request: Request,  # noqa: ARG001
    db: Session = Depends(get_db),
    current_user: Member | None = Depends(get_current_user),
):
    if not current_user:
        return JSONResponse({"ok": False, "error": "unauthorized"}, status_code=401)
    if current_user.id == member_id:
        return JSONResponse({"ok": False, "error": "cannot follow yourself"}, status_code=400)

    target = get_member(db, member_id=member_id)
    if not target:
        return JSONResponse({"ok": False, "error": "member not found"}, status_code=404)

    current_user = get_member_with_following(db, member_id=current_user.id)
    assert current_user is not None

    followed_ids = {member.id for member in current_user.following}
    if member_id in followed_ids:
        current_user.following = [member for member in current_user.following if member.id != member_id]
        action = "unfollow"
    else:
        current_user.following.append(target)
        action = "follow"

    record_log(db, user_id=current_user.id, action_type="关注关系", details=f"{action}:{target.username}")
    db.commit()

    return JSONResponse(
        {
            "ok": True,
            "action": action,
            "following": action == "follow",
            "followers_count": len(target.followers),
        }
    )


@router.get("/member/{member_id}", name="profile")
def profile(
    member_id: int,
    request: Request,
    db: Session = Depends(get_db),
    current_user: Member | None = Depends(get_current_user),
):
    if not current_user:
        return login_redirect(request)

    profile_user = get_member_for_profile(db, member_id=member_id)
    if not profile_user:
        raise HTTPException(status_code=404, detail="Member not found")

    owned_events = list_member_owned_events(db, member_id=profile_user.id)
    participating_events = list_member_participating_events(db, member_id=profile_user.id)
    recent_messages = list_member_recent_messages(db, member_id=profile_user.id)

    viewer_is_admin = is_admin_member(current_user)
    can_manage_profile = _can_manage_profile(current_user, member_id=profile_user.id)
    following_ids = {member.id for member in current_user.following}
    events_upcoming, events_past = split_owned_events(owned_events, now=datetime.now(UTC).replace(tzinfo=None))
    profile_meta, structured = parse_profile_notes(profile_user.notes)
    relation_sections = {"locations": [], "items": [], "events": []}
    if can_manage_profile:
        relation_ids = collect_profile_relation_ids(profile_meta)
        relation_events, relation_items, relation_locations = list_profile_relation_targets(
            db,
            event_ids=relation_ids["event_ids"],
            item_ids=relation_ids["item_ids"],
            location_ids=relation_ids["location_ids"],
        )
        relation_sections = build_profile_relation_sections(
            profile_meta,
            locations=relation_locations,
            items=relation_items,
            events=relation_events,
        )
    member_connections = build_member_connection_view(list_member_connections(db, source_member_id=profile_user.id)) if viewer_is_admin else []

    context = base_template_context()
    context.update(
        {
            "profile_user": profile_user,
            "owned_events": owned_events,
            "participating_events": participating_events,
            "recent_messages": recent_messages,
            "events_upcoming": events_upcoming,
            "events_past": events_past,
            "profile_events": relation_sections["events"],
            "events": list(owned_events),
            "items": list(profile_user.items),
            "locations": list(profile_user.responsible_locations),
            "items_resp": list(profile_user.items),
            "locations_resp": list(profile_user.responsible_locations),
            "notifications": [],
            "user_logs": [],
            "profile_affiliations": relation_sections["locations"],
            "profile_interests": relation_sections["items"],
            "profile_meta": profile_meta,
            "profile_overview": build_member_overview(profile_meta),
            "profile_notes_html": "" if structured else (profile_user.notes or ""),
            "profile_social_links": list(profile_meta.get("social_links") or []),
            "member_connections": member_connections,
            "feedback_entries": [],
            "is_self": current_user.id == profile_user.id,
            "can_edit_profile": can_manage_profile,
            "is_following": profile_user.id in following_ids,
            "show_private_profile_data": can_manage_profile,
            "show_admin_connection_fields": viewer_is_admin,
            "notif_total": 0,
            "logs_total": 0,
            "logs_limit": 20,
            "notif_limit": 20,
            "items_preview": list(profile_user.items)[:6],
            "items_extra": list(profile_user.items)[6:],
            "locations_preview": list(profile_user.responsible_locations)[:6],
            "locations_extra": list(profile_user.responsible_locations)[6:],
            "event_preview": events_upcoming[:6],
            "event_extra": events_upcoming[6:],
            "avatar_entries": (
                [{"url": context["uploaded_attachment_url"](profile_user.photo), "kind": "image", "display_name": "头像"}]
                if profile_user.photo
                else []
            ),
            "structured_notes": structured,
        }
    )
    return render_template(request, "profile.html", context, current_user=current_user)


@router.get("/member/{member_id}/edit", name="edit_profile")
def edit_profile_page(
    member_id: int,
    request: Request,
    db: Session = Depends(get_db),
    current_user: Member | None = Depends(get_current_user),
):
    if not current_user:
        return login_redirect(request)
    if not _can_manage_profile(current_user, member_id=member_id):
        return render_template(
            request,
            "error_403.html",
            _forbidden_context(str(request.url_for("profile", member_id=member_id)), "你没有权限编辑该个人主页。"),
            current_user=current_user,
        )

    member = get_member(db, member_id=member_id)
    if not member:
        raise HTTPException(status_code=404, detail="Member not found")

    profile_meta, structured = parse_profile_notes(member.notes)
    events, items, locations = list_profile_edit_options(db)
    connection_candidates = list_member_connection_candidates(db, exclude_member_id=member.id)
    member_connections = build_member_connection_view(list_member_connections(db, source_member_id=member.id))

    context = base_template_context()
    context.update(
        {
            "member": member,
            "events": events,
            "items": items,
            "locations": locations,
            "profile_meta": profile_meta,
            "structured_notes": structured,
            "relation_lookup": dict(MEMBER_RELATION_TYPES),
            "item_relation_lookup": dict(MEMBER_ITEM_REL_TYPES),
            "event_relation_lookup": dict(MEMBER_EVENT_REL_TYPES),
            "gender_lookup": dict(MEMBER_GENDER_TYPES),
            "can_edit_admin_connection_fields": is_admin_member(current_user),
            "is_self": current_user.id == member.id,
            "connection_candidates": connection_candidates,
            "member_connections": member_connections,
            "member_connection_lookup": dict(MEMBER_CONNECTION_TYPES),
            "member_connection_closeness_lookup": dict(MEMBER_CONNECTION_CLOSENESS),
            "avatar_entries": (
                [{"url": context["uploaded_attachment_url"](member.photo), "kind": "image", "display_name": "头像"}]
                if member.photo
                else []
            ),
        }
    )
    return render_template(request, "edit_profile.html", context, current_user=current_user)


@router.post("/member/{member_id}/edit", name="edit_profile_post")
async def edit_profile_submit(
    member_id: int,
    request: Request,
    db: Session = Depends(get_db),
    current_user: Member | None = Depends(get_current_user),
):
    if not current_user:
        return login_redirect(request)
    if not _can_manage_profile(current_user, member_id=member_id):
        return render_template(
            request,
            "error_403.html",
            _forbidden_context(str(request.url_for("profile", member_id=member_id)), "你没有权限编辑该个人主页。"),
            current_user=current_user,
        )

    member = get_member(db, member_id=member_id)
    if not member:
        raise HTTPException(status_code=404, detail="Member not found")

    form = await request.form()
    name = str(form.get("name", "")).strip()
    if not name:
        flash(request, "姓名不能为空", "danger")
        return RedirectResponse(url=request.url_for("edit_profile", member_id=member.id), status_code=303)

    username = str(form.get("username", "")).strip()
    if username and username != member.username:
        if username_exists_excluding(db, username=username, member_id=member.id):
            flash(request, "用户名已存在", "danger")
            return RedirectResponse(url=request.url_for("edit_profile", member_id=member.id), status_code=303)
        member.username = username

    member.name = name
    member.contact = str(form.get("contact", "")).strip()
    profile_meta, _ = parse_profile_notes(member.notes)
    member.notes = serialize_profile_notes(
        build_profile_meta_from_form(
            form,
            base_meta=profile_meta,
            include_admin_connection_fields=is_admin_member(current_user),
        )
    )
    member.last_modified = datetime.now(UTC).replace(tzinfo=None)

    new_password = str(form.get("password") or form.get("new_password") or "").strip()
    if new_password and current_user.id == member.id:
        member.password_hash = hash_password(new_password)

    if form.get("remove_photo") and member.photo:
        remove_upload(member.photo)
        member.photo = ""

    photo_file = form.get("photo")
    if getattr(photo_file, "filename", ""):
        if member.photo:
            remove_upload(member.photo)
        member.photo = save_upload(photo_file)

    if is_admin_member(current_user):
        submitted_connections = parse_member_connections_form(form, source_member_id=member.id)
        valid_target_ids = {candidate.id for candidate in list_member_connection_candidates(db, exclude_member_id=member.id)}
        existing_connections = list_member_connections(db, source_member_id=member.id)
        to_upsert, to_delete = apply_member_connections(
            existing_connections,
            submitted_connections,
            valid_target_ids=valid_target_ids,
        )
        for connection in to_delete:
            db.delete(connection)
        for connection in to_upsert:
            connection.source_member_id = member.id
            db.add(connection)

    record_log(db, user_id=current_user.id, action_type="编辑个人资料", details=member.username)
    db.commit()

    flash(request, "个人资料已更新", "success")
    return RedirectResponse(url=request.url_for("profile", member_id=member.id), status_code=303)


@router.post("/message/{member_id}", name="post_message")
async def post_message(
    member_id: int,
    request: Request,
    db: Session = Depends(get_db),
    current_user: Member | None = Depends(get_current_user),
):
    if not current_user:
        return login_redirect(request)

    target = get_member(db, member_id=member_id)
    if not target:
        raise HTTPException(status_code=404, detail="Member not found")

    form = await request.form()
    content = str(form.get("content", "")).strip()
    if not content:
        flash(request, "留言不能为空", "warning")
        return RedirectResponse(url=request.url_for("profile", member_id=target.id), status_code=303)

    db.add(Message(sender_id=current_user.id, receiver_id=target.id, content=content))
    record_log(db, user_id=current_user.id, action_type="发送留言", details=f"to={target.username}")
    db.commit()

    flash(request, "留言已发送", "success")
    return RedirectResponse(url=request.url_for("profile", member_id=target.id), status_code=303)
