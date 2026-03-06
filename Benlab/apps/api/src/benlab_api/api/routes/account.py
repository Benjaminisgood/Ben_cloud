"""Account endpoints."""

from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ...db.session import get_db
from ...models import Member
from ...services.admin_identity import is_admin_member
from ...services.member_profiles import parse_profile_notes, serialize_profile_notes
from ..deps import require_api_user

router = APIRouter(tags=["account"])


def _member_description(member: Member) -> str:
    profile_meta, structured = parse_profile_notes(member.notes)
    if structured:
        return str(profile_meta.get("bio") or "").strip()
    return str(member.notes or "").strip()


def _member_role(member: Member) -> str:
    return "admin" if is_admin_member(member) else "user"


@router.get("/account")
def get_account(user: Member = Depends(require_api_user), db: Session = Depends(get_db)):
    users = db.query(Member).order_by(Member.username.asc(), Member.id.asc()).all()
    return {
        "current_user": {
            "id": user.id,
            "username": user.username,
            "name": user.name,
            "role": _member_role(user),
            "description": _member_description(user),
        },
        "users": [
            {
                "id": u.id,
                "username": u.username,
                "name": u.name,
                "description": _member_description(u),
            }
            for u in users
        ],
    }


@router.patch("/account/description")
async def update_description(
    request_body: dict,
    user: Member = Depends(require_api_user),
    db: Session = Depends(get_db),
):
    description = str(request_body.get("description") or "").strip()
    if len(description) > 500:
        raise HTTPException(status_code=400, detail="description too long")

    profile_meta, structured = parse_profile_notes(user.notes)
    if structured:
        profile_meta["bio"] = description
        user.notes = serialize_profile_notes(profile_meta)
    else:
        user.notes = description
    user.last_modified = datetime.now(UTC).replace(tzinfo=None)

    db.commit()
    return {"description": description}


@router.get("/users")
def list_users(user: Member = Depends(require_api_user), db: Session = Depends(get_db)):  # noqa: ARG001
    users = db.query(Member).order_by(Member.username.asc()).all()
    return {"items": [{"id": u.id, "username": u.username} for u in users]}
