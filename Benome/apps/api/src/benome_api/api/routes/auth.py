from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from ...schemas.auth import LoginRequest, LoginResponse, RegisterRequest, UserOut
from ...services.auth import login, register_customer
from ...services.errors import ServiceError
from ..deps import get_db

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", response_model=UserOut, status_code=status.HTTP_201_CREATED)
def register(payload: RegisterRequest, db: Session = Depends(get_db)):
    try:
        user = register_customer(
            db,
            username=payload.username,
            password=payload.password,
            full_name=payload.full_name,
            phone=payload.phone,
        )
    except ServiceError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.detail) from None

    return UserOut(
        id=user.id,
        username=user.username,
        role=user.role,
        full_name=user.full_name,
        phone=user.phone,
    )


@router.post("/login", response_model=LoginResponse)
def login_api(payload: LoginRequest, db: Session = Depends(get_db)):
    try:
        user = login(db, username=payload.username, password=payload.password)
    except ServiceError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.detail) from None

    return LoginResponse(
        user_id=user.id,
        username=user.username,
        role=user.role,
        token=str(user.id),
    )
