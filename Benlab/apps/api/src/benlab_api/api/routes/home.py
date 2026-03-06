"""Home page endpoints."""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from ...db.session import get_db
from ...models import Member
from ...repositories.records_api_repo import (
    count_records,
    count_users,
    list_recent_attachments,
    list_recent_records,
    list_top_tags,
)
from ...services.admin_identity import is_admin_member
from ...services.home_views import build_home_today_response, get_today_context
from ..deps import require_api_user

router = APIRouter(tags=["home"])


@router.get("/home/today")
def get_home_today(
    user: Member = Depends(require_api_user),
    db: Session = Depends(get_db),
):
    """Return home page data for today."""
    today, yesterday, tz_name = get_today_context()
    is_admin = is_admin_member(user)

    public_records = list_recent_records(db, viewer_id=user.id, is_admin=is_admin, limit=10)
    digest_assets = list_recent_attachments(db, limit=5)
    public_count = count_records(db, viewer_id=user.id, is_admin=is_admin)
    user_count = count_users(db)
    top_tags_rows = list_top_tags(db, viewer_id=user.id, is_admin=is_admin, limit=10)

    return build_home_today_response(
        today=today,
        yesterday=yesterday,
        timezone_name=tz_name,
        public_records=public_records,
        digest_assets=digest_assets,
        public_count=public_count,
        user_count=user_count,
        top_tags_rows=top_tags_rows,
    )
