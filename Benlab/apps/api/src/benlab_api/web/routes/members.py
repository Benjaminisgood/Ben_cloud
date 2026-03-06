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
    list_member_owned_events,
    list_member_participating_events,
    list_member_recent_messages,
    list_members_for_listing,
    list_profile_edit_options,
    username_exists_excluding,
)
from benlab_api.services.logs import record_log
from benlab_api.services.member_profiles import (
    MEMBER_EVENT_REL_TYPES,
    MEMBER_ITEM_REL_TYPES,
    MEMBER_RELATION_TYPES,
    build_profile_meta_from_form,
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


@router.get("/members", name="members_list")
def members_list(
    request: Request,
    db: Session = Depends(get_db),
    current_user: Member | None = Depends(get_current_user),
):
    if not current_user:
        return login_redirect(request)

    members = list_members_for_listing(db)
    followed_ids = {member.id for member in current_user.following}
    context = base_template_context()
    context.update(
        {
            "members": members,
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

    following_ids = {member.id for member in current_user.following}
    events_upcoming, events_past = split_owned_events(owned_events, now=datetime.now(UTC).replace(tzinfo=None))

    context = base_template_context()
    context.update(
        {
            "profile_user": profile_user,
            "owned_events": owned_events,
            "participating_events": participating_events,
            "recent_messages": recent_messages,
            "events_upcoming": events_upcoming,
            "events_past": events_past,
            "profile_events": list(owned_events),
            "events": list(owned_events),
            "items": list(profile_user.items),
            "locations": list(profile_user.responsible_locations),
            "items_resp": list(profile_user.items),
            "locations_resp": list(profile_user.responsible_locations),
            "notifications": [],
            "user_logs": [],
            "profile_affiliations": list(profile_user.responsible_locations),
            "profile_interests": list(profile_user.items),
            "profile_meta": {},
            "profile_notes_html": profile_user.notes or "",
            "profile_social_links": [],
            "feedback_entries": [],
            "is_self": current_user.id == profile_user.id,
            "is_following": profile_user.id in following_ids,
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
            "structured_notes": {},
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
    if current_user.id != member_id:
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
    if current_user.id != member_id:
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
    member.notes = serialize_profile_notes(build_profile_meta_from_form(form))
    member.last_modified = datetime.now(UTC).replace(tzinfo=None)

    new_password = str(form.get("password") or form.get("new_password") or "").strip()
    if new_password:
        member.password_hash = hash_password(new_password)

    if form.get("remove_photo") and member.photo:
        remove_upload(member.photo)
        member.photo = ""

    photo_file = form.get("photo")
    if getattr(photo_file, "filename", ""):
        if member.photo:
            remove_upload(member.photo)
        member.photo = save_upload(photo_file)

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
