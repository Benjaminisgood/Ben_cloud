from __future__ import annotations

from fastapi import APIRouter, Depends, Query, Response, status
from sqlalchemy.orm import Session

from benfinance_api.api.deps import require_admin, require_user
from benfinance_api.db.session import get_db
from benfinance_api.schemas.finance_record import FinanceRecordCreate, FinanceRecordRead, FinanceRecordReview, FinanceRecordUpdate
from benfinance_api.services.finance_records import (
    create_finance_record,
    delete_finance_record,
    list_finance_records,
    require_finance_record,
    review_finance_record,
    update_finance_record,
)

router = APIRouter(tags=["finance_records"])


@router.get("/finance-records", response_model=list[FinanceRecordRead])
def get_finance_records(
    user: dict[str, str] = Depends(require_user),
    db: Session = Depends(get_db),
    record_type: str | None = Query(default=None),
    planning_status: str | None = Query(default=None),
    category: str | None = Query(default=None),
    risk_level: str | None = Query(default=None),
    review_status: str | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=200),
) -> list[FinanceRecordRead]:
    return list_finance_records(
        db,
        viewer_username=user["username"],
        viewer_is_admin=user["role"] == "admin",
        record_type=record_type,
        planning_status=planning_status,
        category=category,
        risk_level=risk_level,
        review_status=review_status,
        limit=limit,
    )


@router.post("/finance-records", response_model=FinanceRecordRead, status_code=status.HTTP_201_CREATED)
def post_finance_record(
    payload: FinanceRecordCreate,
    user: dict[str, str] = Depends(require_user),
    db: Session = Depends(get_db),
) -> FinanceRecordRead:
    return create_finance_record(db, payload=payload, actor=user["username"], actor_role=user["role"])


@router.get("/finance-records/{record_id}", response_model=FinanceRecordRead)
def get_finance_record_detail(
    record_id: int,
    user: dict[str, str] = Depends(require_user),
    db: Session = Depends(get_db),
) -> FinanceRecordRead:
    return require_finance_record(
        db,
        record_id=record_id,
        viewer_username=user["username"],
        viewer_is_admin=user["role"] == "admin",
    )


@router.patch("/finance-records/{record_id}", response_model=FinanceRecordRead)
def patch_finance_record(
    record_id: int,
    payload: FinanceRecordUpdate,
    user: dict[str, str] = Depends(require_admin),
    db: Session = Depends(get_db),
) -> FinanceRecordRead:
    return update_finance_record(db, record_id=record_id, payload=payload, actor=user["username"])


@router.post("/finance-records/{record_id}/review", response_model=FinanceRecordRead)
def post_finance_record_review(
    record_id: int,
    payload: FinanceRecordReview,
    user: dict[str, str] = Depends(require_admin),
    db: Session = Depends(get_db),
) -> FinanceRecordRead:
    return review_finance_record(db, record_id=record_id, payload=payload, actor=user["username"])


@router.delete("/finance-records/{record_id}", status_code=status.HTTP_204_NO_CONTENT)
def remove_finance_record(
    record_id: int,
    _: dict[str, str] = Depends(require_admin),
    db: Session = Depends(get_db),
) -> Response:
    delete_finance_record(db, record_id=record_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
