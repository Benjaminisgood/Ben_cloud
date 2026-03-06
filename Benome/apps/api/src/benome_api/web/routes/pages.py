from __future__ import annotations

import json
import secrets

from fastapi import APIRouter, Depends, Query, Request
from fastapi.responses import HTMLResponse, RedirectResponse

from ...core.config import get_settings
from ...db.session import get_db
from ...repositories.users_repo import create_user, get_user_by_username
from ...services.properties import get_public_property_detail
from ...services.property_media import get_property_media_list
from ...services.sso import verify_sso_token
from ..deps import get_session_user
from ..templating import render_template

router = APIRouter(tags=["pages"])


@router.get("/", response_class=HTMLResponse)
def home(request: Request):
    return render_template(
        request,
        "index.html",
        {
            "title": "ling居家",
            "subtitle": "随时浏览房源，填写信息即可预订，管理员审核后锁定日期",
        },
    )


@router.get("/auth/sso", response_class=HTMLResponse)
def sso_callback(
    token: str = Query(...),
    request: Request = None,
    db=Depends(get_db),
):
    """接收来自 Benbot 的 SSO 跳转，验证 token 并建立本地会话。"""
    settings = get_settings()
    payload = verify_sso_token(settings.SSO_SECRET, token)

    if not payload:
        return HTMLResponse(
            """<!doctype html>
<html lang="zh-CN"><head><meta charset="UTF-8"><title>登录失败</title></head>
<body><script>
try { sessionStorage.setItem('benome_flash', JSON.stringify({msg:'Benbot 登录凭证无效或已过期，请重新登录', err:true})); } catch(e){}
window.location.href = '/';
</script><p>正在跳转...</p></body></html>""",
            status_code=200,
        )

    username = str(payload.get("u", "")).strip()
    benbot_role = str(payload.get("r", "user"))

    if not username:
        return HTMLResponse(
            """<!doctype html>
<html lang="zh-CN"><head><meta charset="UTF-8"><title>登录失败</title></head>
<body><script>
try { sessionStorage.setItem('benome_flash', JSON.stringify({msg:'SSO token 缺少用户名', err:true})); } catch(e){}
window.location.href = '/';
</script><p>正在跳转...</p></body></html>""",
            status_code=200,
        )

    # Benbot admin → Benome admin；其他角色 → customer
    benome_role = "admin" if benbot_role == "admin" else "customer"

    user = get_user_by_username(db, username=username)
    if not user:
        # 首次 SSO 登录，自动创建本地账号
        user = create_user(
            db,
            username=username,
            password=secrets.token_hex(32),
            role=benome_role,
            full_name=username,
            phone="",
        )
        db.commit()
        db.refresh(user)

    # 设置后端 session cookie
    from ..deps import login_session
    login_session(request, user)

    session_json = json.dumps(
        {"userId": user.id, "username": user.username, "role": user.role}
    )

    # Redirect based on role: admin → admin dashboard, customer → customer dashboard
    redirect_path = "/admin/dashboard" if user.role == "admin" else "/dashboard"
    
    return HTMLResponse(
        f"""<!doctype html>
<html lang="zh-CN"><head><meta charset="UTF-8"><title>正在登录...</title></head>
<body><script>
try {{
    localStorage.setItem('benome_session_v1', {json.dumps(session_json)});
    sessionStorage.setItem('benome_flash', JSON.stringify({{msg:'已通过 Benbot 账号登录：{user.username}', err:false}}));
}} catch(e) {{}}
window.location.href = '{redirect_path}';
</script><p>正在跳转，请稍候...</p></body></html>""",
        status_code=200,
    )


@router.get("/login", response_class=HTMLResponse)
def login_page(request: Request):
    """登录页面"""
    return render_template(
        request,
        "login.html",
        {},
    )


@router.get("/goto/benome", response_class=HTMLResponse)
def goto_benome(request: Request):
    """跳转到 Benbot SSO"""
    settings = get_settings()
    # 构建 SSO 跳转 URL
    host = request.url.hostname
    proto = request.url.scheme
    callback_url = f"{proto}://{host}/auth/sso"
    
    # Benbot SSO 地址（从环境变量读取或使用默认值）
    benbot_base = settings.BENBOT_BASE_URL or "http://localhost:8100"
    sso_url = f"{benbot_base}/sso/benome?callback={callback_url}"
    
    return RedirectResponse(sso_url, status_code=302)


@router.get("/dashboard", response_class=HTMLResponse)
def dashboard_page(request: Request, db=Depends(get_db)):
    """Customer/tenant dashboard page."""
    user = get_session_user(request, db)
    if not user:
        # Not logged in via SSO, redirect to home
        return RedirectResponse("/", status_code=302)
    
    # 允许管理员访问用户视图（用于测试或查看用户视角）
    # 不再强制跳转到 admin dashboard
    
    return render_template(
        request,
        "dashboard.html",
        {
            "title": "我的房源",
            "current_user": user,
        },
    )


@router.get("/admin/dashboard", response_class=HTMLResponse)
def admin_dashboard_page(request: Request, db=Depends(get_db)):
    """Admin dashboard page."""
    user = get_session_user(request, db)
    if not user or user.role != "admin":
        # Not logged in or not admin, redirect to home
        return RedirectResponse("/", status_code=302)
    
    return render_template(
        request,
        "admin_dashboard.html",
        {
            "title": "管理控制台",
            "current_user": user,
        },
    )


@router.get("/properties/{property_id}", response_class=HTMLResponse)
def property_detail_page(property_id: int, request: Request, db=Depends(get_db)):
    """房间详情页面（带媒体展示）"""
    user = get_session_user(request, db)
    
    try:
        property_obj = get_public_property_detail(db, property_id=property_id)
    except Exception:
        return RedirectResponse("/properties", status_code=302)
    
    # 获取媒体列表
    media_list = get_property_media_list(db, property_id)
    
    # 转换为字典列表供模板使用
    media_data = [
        {
            "id": m.id,
            "property_id": m.property_id,
            "media_type": m.media_type,
            "oss_key": m.oss_key,
            "public_url": m.public_url,
            "file_size": m.file_size,
            "mime_type": m.mime_type,
            "title": m.title,
            "description": m.description,
            "sort_order": m.sort_order,
            "is_cover": m.is_cover,
            "is_active": m.is_active,
            "created_at": m.created_at,
            "updated_at": m.updated_at,
        }
        for m in media_list
    ]
    
    # 转换为类似 PropertyOut 的字典
    property_data = {
        "id": property_obj.id,
        "title": property_obj.title,
        "description": property_obj.description,
        "city": property_obj.city,
        "address": property_obj.address,
        "price_per_night": property_obj.price_per_night,
        "max_guests": property_obj.max_guests,
        "is_active": property_obj.is_active,
        "created_by_admin_id": property_obj.created_by_admin_id,
        "created_at": property_obj.created_at,
        "updated_at": property_obj.updated_at,
        "media": media_data,
    }
    
    return render_template(
        request,
        "property_detail.html",
        {
            "title": property_obj.title,
            "property": property_data,
            "current_user": user,
        },
    )


@router.get("/admin/properties/{property_id}/media", response_class=HTMLResponse)
def admin_media_manage_page(property_id: int, request: Request, db=Depends(get_db)):
    """管理员媒体管理页面"""
    user = get_session_user(request, db)
    if not user or user.role != "admin":
        return RedirectResponse("/", status_code=302)
    
    try:
        property_obj = get_public_property_detail(db, property_id=property_id)
    except Exception:
        return RedirectResponse("/admin/dashboard", status_code=302)
    
    property_data = {
        "id": property_obj.id,
        "title": property_obj.title,
    }
    
    return render_template(
        request,
        "admin_media_manage.html",
        {
            "title": "管理媒体",
            "property": property_data,
            "current_user": user,
        },
    )


@router.get("/properties", response_class=HTMLResponse)
def properties_list_page(request: Request, db=Depends(get_db)):
    """浏览房源列表页面"""
    user = get_session_user(request, db)
    if not user:
        return RedirectResponse("/", status_code=302)
    
    return render_template(
        request,
        "properties.html",
        {
            "title": "浏览房源",
            "current_user": user,
        },
    )


@router.get("/bookings", response_class=HTMLResponse)
def bookings_list_page(request: Request, db=Depends(get_db)):
    """我的预订列表页面"""
    user = get_session_user(request, db)
    if not user:
        return RedirectResponse("/", status_code=302)
    
    return render_template(
        request,
        "bookings.html",
        {
            "title": "我的预订",
            "current_user": user,
        },
    )


@router.get("/bookings/{booking_id}", response_class=HTMLResponse)
def booking_detail_page(booking_id: int, request: Request, db=Depends(get_db)):
    """预订详情页面"""
    user = get_session_user(request, db)
    if not user:
        return RedirectResponse("/", status_code=302)
    
    return render_template(
        request,
        "booking_detail.html",
        {
            "title": "预订详情",
            "current_user": user,
            "booking_id": booking_id,
        },
    )


@router.get("/admin/properties/{property_id}/edit", response_class=HTMLResponse)
def admin_property_edit_page(property_id: int, request: Request, db=Depends(get_db)):
    """管理员编辑房源页面"""
    user = get_session_user(request, db)
    if not user or user.role != "admin":
        return RedirectResponse("/", status_code=302)
    
    return render_template(
        request,
        "admin_property_edit.html",
        {
            "title": "编辑房源",
            "current_user": user,
            "property_id": property_id,
        },
    )


@router.get("/admin/properties/create", response_class=HTMLResponse)
def admin_property_create_page(request: Request, db=Depends(get_db)):
    """管理员创建房源页面"""
    user = get_session_user(request, db)
    if not user or user.role != "admin":
        return RedirectResponse("/", status_code=302)
    
    return render_template(
        request,
        "admin_property_create.html",
        {
            "title": "添加房源",
            "current_user": user,
        },
    )


@router.get("/properties/{property_id}/book", response_class=HTMLResponse)
def booking_create_page(property_id: int, request: Request, db=Depends(get_db)):
    """用户创建预订页面"""
    user = get_session_user(request, db)
    if not user:
        # 未登录，重定向到登录页
        return RedirectResponse("/login", status_code=302)
    
    return render_template(
        request,
        "booking_create.html",
        {
            "title": "预订房源",
            "current_user": user,
            "property_id": property_id,
        },
    )


@router.get("/admin/calendar", response_class=HTMLResponse)
def admin_calendar_page(request: Request, db=Depends(get_db)):
    """管理员房态日历页面"""
    user = get_session_user(request, db)
    if not user or user.role != "admin":
        return RedirectResponse("/", status_code=302)
    
    return render_template(
        request,
        "admin_calendar.html",
        {
            "title": "房态日历",
            "current_user": user,
        },
    )


@router.get("/change-password", response_class=HTMLResponse)
def change_password_page(request: Request, db=Depends(get_db)):
    """用户修改密码页面"""
    user = get_session_user(request, db)
    if not user:
        return RedirectResponse("/login", status_code=302)
    
    return render_template(
        request,
        "change_password.html",
        {
            "title": "修改密码",
            "current_user": user,
        },
    )


@router.get("/admin/statistics", response_class=HTMLResponse)
def admin_statistics_page(request: Request, db=Depends(get_db)):
    """管理员数据统计页面"""
    user = get_session_user(request, db)
    if not user or user.role != "admin":
        return RedirectResponse("/", status_code=302)
    
    return render_template(
        request,
        "admin_statistics.html",
        {
            "title": "数据统计",
            "current_user": user,
        },
    )


@router.get("/admin/users", response_class=HTMLResponse)
def admin_users_page(request: Request, db=Depends(get_db)):
    """管理员用户管理页面"""
    user = get_session_user(request, db)
    if not user or user.role != "admin":
        return RedirectResponse("/", status_code=302)
    
    return render_template(
        request,
        "admin_users.html",
        {
            "title": "用户管理",
            "current_user": user,
        },
    )


@router.get("/admin/settings", response_class=HTMLResponse)
def admin_settings_page(request: Request, db=Depends(get_db)):
    """管理员系统设置页面"""
    user = get_session_user(request, db)
    if not user or user.role != "admin":
        return RedirectResponse("/", status_code=302)
    
    return render_template(
        request,
        "admin_settings.html",
        {
            "title": "系统设置",
            "current_user": user,
        },
    )


@router.get("/admin/bookings", response_class=HTMLResponse)
def admin_bookings_page(request: Request, db=Depends(get_db)):
    """管理员预订管理页面"""
    user = get_session_user(request, db)
    if not user or user.role != "admin":
        return RedirectResponse("/", status_code=302)
    
    return render_template(
        request,
        "admin_bookings.html",
        {
            "title": "预订管理",
            "current_user": user,
        },
    )


@router.get("/profile", response_class=HTMLResponse)
def profile_page(request: Request, db=Depends(get_db)):
    """个人资料页面"""
    user = get_session_user(request, db)
    if not user:
        return RedirectResponse("/", status_code=302)
    
    return render_template(
        request,
        "profile.html",
        {
            "title": "个人资料",
            "current_user": user,
        },
    )


@router.get("/logout", response_class=HTMLResponse)
def logout_page(request: Request):
    """退出登录页面"""
    # 清除后端 session
    request.session.clear()
    
    # 返回 HTML 清除前端 localStorage 并跳转
    return HTMLResponse(
        """<!doctype html>
<html lang="zh-CN"><head><meta charset="UTF-8"><title>正在退出...</title></head>
<body><script>
try {
    localStorage.removeItem('benome_session_v1');
    sessionStorage.clear();
} catch(e) {}
window.location.href = '/';
</script><p>正在退出，请稍候...</p></body></html>""",
        status_code=200,
    )
