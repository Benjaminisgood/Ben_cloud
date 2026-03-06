from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ...db.session import get_db
from ..deps import require_api_user
from ...models import User

router = APIRouter(tags=["account"])


@router.get("/account")
def get_account(user: User = Depends(require_api_user), db: Session = Depends(get_db)):
    users = db.query(User).filter_by(is_active=True).order_by(User.username.asc(), User.id.asc()).all()
    return {
        "current_user": {
            "id": user.id,
            "username": user.username,
            "role": user.role,
            "description": user.description or "",
        },
        "users": [{"id": u.id, "username": u.username, "description": u.description or ""} for u in users],
    }


@router.patch("/account/description")
async def update_description(
    request_body: dict,
    user: User = Depends(require_api_user),
    db: Session = Depends(get_db),
):
    description = str(request_body.get("description") or "").strip()
    if len(description) > 500:
        raise HTTPException(status_code=400, detail="description too long")
    user.description = description
    db.commit()
    return {"description": user.description}


@router.get("/users")
def list_users(user: User = Depends(require_api_user), db: Session = Depends(get_db)):
    users = db.query(User).filter_by(is_active=True).order_by(User.username.asc()).all()
    return {"items": [{"id": u.id, "username": u.username} for u in users]}
