from fastapi import APIRouter, Request, Depends
from fastapi.responses import RedirectResponse, HTMLResponse

from apps.core.config import settings
from apps.services.sso import verify_sso_token

router = APIRouter()


@router.get("/auth/sso")
async def auth_sso(request: Request):
    """Handle SSO login from Benbot portal.
    
    Validates the SSO token and redirects to the main page with session.
    """
    token = request.query_params.get("token")
    if not token:
        return HTMLResponse(content="Missing token", status_code=400)
    
    payload = verify_sso_token(settings.sso_secret, token)
    if not payload:
        return HTMLResponse(content="Invalid or expired token", status_code=401)
    
    username = payload.get("u", "anonymous")
    role = payload.get("r", "user")
    
    # Redirect to main page - in a real implementation, you would set a session cookie here
    # For now, we just redirect to the homepage
    return RedirectResponse(url="/", status_code=302)
