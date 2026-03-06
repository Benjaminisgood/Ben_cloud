from urllib.parse import quote

from fastapi import APIRouter, HTTPException, Request, status
from fastapi.responses import RedirectResponse, JSONResponse

from benfer_api.utils.auth import create_session_token, verify_sso_token

router = APIRouter()


def _extract_token(request: Request) -> str:
    token = request.query_params.get("token")
    if token:
        return token

    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Missing token parameter",
    )


@router.get("/sso")
async def sso_auth_get(request: Request):
    """
    SSO authentication endpoint for Benbot integration (GET method).
    Validates token from query parameter and redirects to main page with session.
    Token format matches Benbot's create_sso_token: base64(json_data.signature)
    """
    token = _extract_token(request)
    result = verify_sso_token(token)
    session_token, _exp = create_session_token(
        user_id=result["user_id"],
        role=result.get("role"),
    )

    # Redirect with Benfer-local session token.
    redirect_url = f"/?token={quote(session_token, safe='')}"
    return RedirectResponse(url=redirect_url, status_code=302)


@router.post("/sso")
async def sso_auth_post(request: Request):
    """
    SSO authentication endpoint for Benbot integration (POST method).
    Validates token from form data and returns user info as JSON.
    Token format matches Benbot's create_sso_token: base64(json_data.signature)
    """
    token = request.query_params.get("token")
    if not token:
        try:
            body = await request.form()
            token = body.get("token")
        except Exception:
            token = None

    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing token parameter",
        )

    result = verify_sso_token(token)
    session_token, session_exp = create_session_token(
        user_id=result["user_id"],
        role=result.get("role"),
    )

    return JSONResponse(
        content={
            "user_id": result["user_id"],
            "role": result.get("role"),
            "session_token": session_token,
            "session_expires_at": session_exp,
            "message": "SSO authentication successful",
        }
    )
