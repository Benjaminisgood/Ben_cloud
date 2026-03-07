from __future__ import annotations

import base64
import hashlib
import hmac
import html
import json
from pathlib import Path
import re
import secrets
import time

from fastapi import APIRouter, HTTPException, Request, status
from fastapi.responses import FileResponse, HTMLResponse, RedirectResponse, Response

from models.admin import User
from repositories.user import user_repository
from schemas.users import UserCreate
from services.labdocs_service import ResourceNotFoundError, labdocs_service
from settings import settings
from utils.jwt import create_token_pair, verify_token

router = APIRouter(tags=["sso"])

_SSO_EMAIL_DOMAIN = "benbot.app"
_MIN_PASSWORD_LENGTH = 12
_PROJECT_ROOT = Path(__file__).resolve().parent.parent
_DOCS_SITE_DIR = Path(settings.DOCS_SITE_DIR)
_APP_SITE_DIR = _PROJECT_ROOT / "app"


def verify_sso_token(sso_secret: str, token: str) -> dict | None:
    """Verify Benbot SSO token; returns payload or None when invalid."""
    try:
        decoded = base64.urlsafe_b64decode(token.encode()).decode()
        dot_pos = decoded.rfind(".")
        if dot_pos == -1:
            return None
        data, sig = decoded[:dot_pos], decoded[dot_pos + 1 :]
        expected = hmac.new(
            sso_secret.encode(), data.encode(), hashlib.sha256
        ).hexdigest()
        if not hmac.compare_digest(sig, expected):
            return None
        payload = json.loads(data)
        if payload.get("e", 0) < time.time():
            return None
        return payload
    except Exception:
        return None


def _normalize_username(raw: str) -> str:
    text = re.sub(r"[^a-zA-Z0-9_]", "_", raw.strip()).strip("_")
    if not text:
        text = "sso_user"
    if len(text) <= 20:
        return text

    digest = hashlib.sha1(text.encode("utf-8")).hexdigest()[:6]
    return f"{text[:13]}_{digest}"


def _normalize_email(username: str) -> str:
    return f"{username}@{_SSO_EMAIL_DOMAIN}"


def _random_password() -> str:
    # Ensure generated password contains letters and digits.
    token = secrets.token_hex(max(_MIN_PASSWORD_LENGTH, 16))
    return f"Sso{token}9"


def _is_admin(role: str) -> bool:
    return role.strip().lower() == "admin"


async def _find_or_create_user(*, username: str, role: str) -> User:
    user = await user_repository.get_by_username(username)
    if user is None:
        user = await user_repository.get_by_email(_normalize_email(username))

    if user is None:
        user = await user_repository.create_user(
            UserCreate(
                username=username,
                email=_normalize_email(username),
                password=_random_password(),
                is_active=True,
                is_superuser=_is_admin(role),
                role_ids=[],
                dept_id=0,
            )
        )
        return user

    dirty = False
    target_superuser = _is_admin(role)
    if not user.is_active:
        user.is_active = True
        dirty = True
    if user.is_superuser != target_superuser:
        user.is_superuser = target_superuser
        dirty = True
    if dirty:
        await user.save()
    return user


def _portal_html(*, username: str, role: str, user_id: int) -> str:
    safe_username = html.escape(username)
    safe_role = html.escape(role)
    return f"""<!doctype html>
<html lang="zh-CN">
  <head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    <title>Benfast Portal</title>
    <style>
      body {{
        margin: 0;
        font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
        background: linear-gradient(120deg, #f4f6f8 0%, #e8eff8 100%);
        color: #0f172a;
      }}
      .wrap {{
        max-width: 720px;
        margin: 56px auto;
        background: #ffffff;
        border-radius: 14px;
        padding: 28px;
        box-shadow: 0 12px 32px rgba(15, 23, 42, 0.08);
      }}
      h1 {{
        margin: 0 0 10px;
        font-size: 28px;
      }}
      p {{
        margin: 6px 0;
      }}
      code {{
        background: #f1f5f9;
        border-radius: 6px;
        padding: 2px 6px;
      }}
      .links {{
        margin-top: 18px;
        display: flex;
        gap: 12px;
        flex-wrap: wrap;
      }}
      .links a {{
        text-decoration: none;
        color: #ffffff;
        background: #2563eb;
        border-radius: 8px;
        padding: 10px 14px;
      }}
    </style>
  </head>
  <body>
    <main class="wrap">
      <h1>Benfast 已通过 Benbot SSO 登录</h1>
      <p><strong>用户:</strong> <code>{safe_username}</code></p>
      <p><strong>角色:</strong> <code>{safe_role}</code></p>
      <p><strong>本地用户ID:</strong> <code>{user_id}</code></p>
      <div class="links">
        <a href="/api/v1/base/userinfo">查看当前用户信息</a>
        <a href="/api/v1/base/health">查看 API 健康状态</a>
        <a href="/auth/logout">退出当前会话</a>
      </div>
    </main>
  </body>
</html>
"""


def _portal_error_html(message: str) -> str:
    safe_message = html.escape(message)
    return f"""<!doctype html>
<html lang="zh-CN">
  <head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    <title>Benfast Portal</title>
    <style>
      body {{
        margin: 0;
        font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
        background: #f8fafc;
        color: #0f172a;
      }}
      .wrap {{
        max-width: 680px;
        margin: 56px auto;
        background: #ffffff;
        border-radius: 14px;
        padding: 28px;
        box-shadow: 0 8px 28px rgba(15, 23, 42, 0.08);
      }}
      a {{
        color: #2563eb;
      }}
    </style>
  </head>
  <body>
    <main class="wrap">
      <h1>当前未登录 Benfast</h1>
      <p>{safe_message}</p>
      <p>请从 Benbot 门户重新进入本项目。</p>
    </main>
  </body>
</html>
"""


def _docs_not_ready_html() -> str:
    return """<!doctype html>
<html lang="zh-CN">
  <head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    <title>Benfast Docs</title>
    <style>
      body {
        margin: 0;
        font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
        background: #f8fafc;
        color: #0f172a;
      }
      .wrap {
        max-width: 760px;
        margin: 56px auto;
        background: #ffffff;
        border-radius: 14px;
        padding: 28px;
        box-shadow: 0 8px 28px rgba(15, 23, 42, 0.08);
      }
      pre {
        background: #0f172a;
        color: #e2e8f0;
        border-radius: 8px;
        padding: 14px;
        overflow-x: auto;
      }
    </style>
  </head>
  <body>
    <main class="wrap">
      <h1>Benfast 文档站尚未构建</h1>
      <p>请先在项目根目录构建文档静态站点：</p>
      <pre>cd /Users/ben/Desktop/Ben_cloud/Benfast
make docs-build</pre>
      <p>构建完成后刷新当前页面即可。</p>
    </main>
  </body>
</html>
"""


def _app_not_ready_html() -> str:
    return """<!doctype html>
<html lang="zh-CN">
  <head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    <title>Benfast App</title>
    <style>
      body {
        margin: 0;
        font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
        background: #f8fafc;
        color: #0f172a;
      }
      .wrap {
        max-width: 760px;
        margin: 56px auto;
        background: #ffffff;
        border-radius: 14px;
        padding: 28px;
        box-shadow: 0 8px 28px rgba(15, 23, 42, 0.08);
      }
    </style>
  </head>
  <body>
    <main class="wrap">
      <h1>Benfast 协作文档应用未就绪</h1>
      <p>请确认目录存在：</p>
      <p><code>/Users/ben/Desktop/Ben_cloud/Benfast/app</code></p>
    </main>
  </body>
</html>
"""


async def _get_authenticated_user(request: Request) -> tuple[User | None, str | None]:
    token = request.cookies.get(settings.SSO_TOKEN_COOKIE_NAME, "")
    if not token:
        return None, "未找到登录凭据。"

    try:
        payload = verify_token(token, token_type="access")
    except Exception:
        return None, "登录状态已过期或无效。"

    user = await User.filter(id=payload.user_id).first()
    if user is None:
        return None, "用户不存在，请重新从 Benbot 登录。"
    return user, None


def _resolve_doc_path(doc_path: str) -> Path | None:
    base = _DOCS_SITE_DIR.resolve()
    normalized = doc_path.strip("/")
    if not normalized:
        candidates = [base / "index.html"]
    else:
        candidates = [base / normalized, base / normalized / "index.html"]
        if "." not in Path(normalized).name:
            candidates.append(base / f"{normalized}.html")

    for candidate in candidates:
        try:
            resolved = candidate.resolve()
        except OSError:
            continue
        if not str(resolved).startswith(str(base)):
            continue
        if resolved.is_file():
            return resolved
    return None


def _resolve_app_path(app_path: str) -> Path | None:
    base = _APP_SITE_DIR.resolve()
    normalized = app_path.strip("/")
    if not normalized:
        candidates = [base / "books" / "index.html", base / "index.html"]
    else:
        candidates = [base / normalized, base / normalized / "index.html"]

    for candidate in candidates:
        try:
            resolved = candidate.resolve()
        except OSError:
            continue
        if not str(resolved).startswith(str(base)):
            continue
        if resolved.is_file():
            return resolved
    return None


def _resolve_virtual_app_page(app_path: str) -> Path | None:
    normalized = app_path.strip("/")
    if not normalized:
        return _resolve_app_path("")

    parts = [segment for segment in normalized.split("/") if segment]
    if parts == ["books"]:
        return _resolve_app_path("books")
    if len(parts) == 2 and parts[0] == "books":
        return _resolve_app_path("book")
    if len(parts) == 3 and parts[0] == "books" and parts[2] == "settings":
        return _resolve_app_path("book")
    if len(parts) == 3 and parts[0] == "books" and parts[2] == "outline":
        return _resolve_app_path("outline")
    if len(parts) == 4 and parts[0] == "books" and parts[2] == "pages":
        return _resolve_app_path("editor")
    if (
        len(parts) == 5
        and parts[0] == "books"
        and parts[2] == "pages"
        and parts[4] == "preview"
    ):
        return _resolve_app_path("preview")
    if len(parts) == 3 and parts[0] == "books" and parts[2] == "publish":
        return _resolve_app_path("publish")
    return None


@router.get("/health")
async def health() -> dict[str, str]:
    return {
        "status": "healthy",
        "service": "Benfast",
        "version": settings.VERSION,
    }


@router.get("/auth/sso")
async def sso_callback(token: str) -> RedirectResponse:
    if not settings.SSO_SECRET.strip():
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="SSO is not configured",
        )

    payload = verify_sso_token(settings.SSO_SECRET, token)
    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired SSO token",
        )

    username = _normalize_username(str(payload.get("u", "")))
    role = str(payload.get("r", "user")).strip().lower() or "user"
    user = await _find_or_create_user(username=username, role=role)
    await user_repository.update_last_login(user.id)

    access_token, refresh_token = create_token_pair(user.id)
    response = RedirectResponse(url=settings.SSO_REDIRECT_PATH, status_code=302)
    response.set_cookie(
        key=settings.SSO_TOKEN_COOKIE_NAME,
        value=access_token,
        max_age=settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        httponly=True,
        samesite="lax",
        secure=False,
        path="/",
    )
    response.set_cookie(
        key=settings.SSO_REFRESH_COOKIE_NAME,
        value=refresh_token,
        max_age=settings.JWT_REFRESH_TOKEN_EXPIRE_DAYS * 24 * 60 * 60,
        httponly=True,
        samesite="lax",
        secure=False,
        path="/",
    )
    return response


@router.get("/auth/logout")
async def logout() -> RedirectResponse:
    response = RedirectResponse(url="/", status_code=302)
    response.delete_cookie(settings.SSO_TOKEN_COOKIE_NAME, path="/")
    response.delete_cookie(settings.SSO_REFRESH_COOKIE_NAME, path="/")
    return response


@router.get("/", response_class=HTMLResponse, include_in_schema=False)
async def root_page(request: Request):
    _, error = await _get_authenticated_user(request)
    if error:
        return HTMLResponse(_portal_error_html(error), status_code=401)
    return RedirectResponse(url="/kb/", status_code=302)


@router.get("/portal", response_class=HTMLResponse)
async def portal(request: Request) -> HTMLResponse:
    _, error = await _get_authenticated_user(request)
    if error:
        return HTMLResponse(_portal_error_html(error), status_code=401)
    return RedirectResponse(url="/kb/", status_code=302)


@router.get("/kb", include_in_schema=False)
async def docs_shortcut(request: Request):
    _, error = await _get_authenticated_user(request)
    if error:
        return HTMLResponse(_portal_error_html(error), status_code=401)
    return RedirectResponse(url="/kb/", status_code=302)


@router.get("/kb/media/{book_id}/{stored_name:path}", include_in_schema=False)
async def docs_media(request: Request, book_id: str, stored_name: str):
    _, error = await _get_authenticated_user(request)
    if error:
        return HTMLResponse(_portal_error_html(error), status_code=401)

    try:
        asset = labdocs_service.get_book_asset(book_id, stored_name)
    except ResourceNotFoundError:
        return HTMLResponse(_portal_error_html("文档附件不存在。"), status_code=404)

    meta = asset["meta"]
    headers = {
        "Cache-Control": "private, max-age=300",
        "Content-Disposition": f'inline; filename="{Path(str(meta["original_name"])).name}"',
    }
    return Response(
        content=asset["content"],
        media_type=str(meta.get("content_type") or "application/octet-stream"),
        headers=headers,
    )


@router.get("/kb/{doc_path:path}", include_in_schema=False)
async def docs_site(request: Request, doc_path: str):
    _, error = await _get_authenticated_user(request)
    if error:
        return HTMLResponse(_portal_error_html(error), status_code=401)

    if not _DOCS_SITE_DIR.exists():
        return HTMLResponse(_docs_not_ready_html(), status_code=503)

    target = _resolve_doc_path(doc_path)
    if target is None:
        return HTMLResponse(_portal_error_html("文档页面不存在。"), status_code=404)
    return FileResponse(target)


@router.get("/workspace", include_in_schema=False)
async def workspace_shortcut(request: Request):
    _, error = await _get_authenticated_user(request)
    if error:
        return HTMLResponse(_portal_error_html(error), status_code=401)
    return RedirectResponse(url="/app/", status_code=302)


@router.get("/app", include_in_schema=False)
@router.get("/app/{asset_path:path}", include_in_schema=False)
async def collab_app_site(request: Request, asset_path: str = ""):
    _, error = await _get_authenticated_user(request)
    if error:
        return HTMLResponse(_portal_error_html(error), status_code=401)

    if not _APP_SITE_DIR.exists():
        return HTMLResponse(_app_not_ready_html(), status_code=503)

    target = _resolve_app_path(asset_path)
    if target is None:
        target = _resolve_virtual_app_page(asset_path)
    if target is None and "." not in Path(asset_path).name:
        target = _resolve_app_path("")

    if target is None:
        return HTMLResponse(_portal_error_html("协作文档应用页面不存在。"), status_code=404)
    return FileResponse(target)
