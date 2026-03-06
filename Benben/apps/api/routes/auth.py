from __future__ import annotations

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import JSONResponse, RedirectResponse

from ...core.auth import set_session_user, validate_sso_token

router = APIRouter(tags=["auth"])


@router.get("/auth/sso")
async def sso_auth_get(request: Request):
    token = request.query_params.get("token")
    if not token:
        raise HTTPException(status_code=401, detail="Missing token parameter")

    user = validate_sso_token(token)
    set_session_user(request, username=user["username"], role=user["role"])
    return RedirectResponse(url="/", status_code=302)


@router.post("/auth/sso")
async def sso_auth_post(request: Request):
    token = request.query_params.get("token")
    if not token:
        try:
            form = await request.form()
            token = str(form.get("token") or "")
        except Exception:
            token = ""

    if not token:
        raise HTTPException(status_code=401, detail="Missing token parameter")

    user = validate_sso_token(token)
    set_session_user(request, username=user["username"], role=user["role"])

    return JSONResponse(
        content={
            "user_id": user["username"],
            "role": user["role"],
            "message": "SSO authentication successful",
        }
    )


@router.post("/auth/logout")
async def logout(request: Request):
    request.session.clear()
    return JSONResponse(content={"ok": True})
