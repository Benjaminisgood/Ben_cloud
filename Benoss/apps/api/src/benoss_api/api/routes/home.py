"""Home page endpoints."""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from ...db.session import get_db
from ...repositories.home_repo import (
    count_public_records,
    count_users,
    list_public_digest_assets,
    list_public_records,
    list_top_public_tags,
)
from ...services.home_views import build_home_today_response, get_today_context
from ...models import User
from ..deps import require_api_user

router = APIRouter(tags=["home"])


@router.get("/home/today")
def get_home_today(
    user: User = Depends(require_api_user),
    db: Session = Depends(get_db),
):
    """Return home page data for today."""
    today, yesterday, tz_name = get_today_context()

    public_records = list_public_records(db, limit=10)
    digest_assets = list_public_digest_assets(db, limit=5)
    public_count = count_public_records(db)
    user_count = count_users(db)
    top_tags_rows = list_top_public_tags(db, limit=10)

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
