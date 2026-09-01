from fastapi import APIRouter, Depends, HTTPException, Request, Form
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session
from typing import Optional
import json

from database import get_db
from models import User, Post, SiteSettings
from auth import get_current_user, require_role

router = APIRouter(prefix="/admin", tags=["admin"])


@router.get("/")
async def admin_panel(
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("admin")),
):
    """Главная страница админ-панели"""
    settings = db.query(SiteSettings).first()
    if not settings:
        settings = SiteSettings(theme_colors={})
        db.add(settings)
        db.commit()
        db.refresh(settings)

    users_count = db.query(User).count()
    posts_count = db.query(Post).count()

    return request.app.state.templates.TemplateResponse(
        "admin/dashboard.html",
        {
            "request": request,
            "user": current_user,
            "settings": settings,
            "users_count": users_count,
            "posts_count": posts_count,
        },
    )


@router.get("/users")
async def list_users(
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("admin")),
):
    """Список всех пользователей"""
    users = db.query(User).all()
    return request.app.state.templates.TemplateResponse(
        "admin/users.html",
        {"request": request, "user": current_user, "users": users},
    )


@router.post("/users/{user_id}/role")
async def change_user_role(
    user_id: int,
    role: str = Form(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("admin")),
):
    """Изменение роли пользователя"""
    if role not in ["admin", "moderator", "user"]:
        raise HTTPException(status_code=400, detail="Invalid role")

    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    user.role = role
    db.commit()
    return RedirectResponse(url="/admin/users", status_code=303)


@router.get("/posts")
async def list_posts(
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("admin")),
):
    """Список всех постов"""
    posts = db.query(Post).all()
    return request.app.state.templates.TemplateResponse(
        "admin/posts.html",
        {"request": request, "user": current_user, "posts": posts},
    )


@router.post("/posts/{post_id}/delete")
async def delete_post(
    post_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("admin")),
):
    """Удаление поста"""
    post = db.query(Post).filter(Post.id == post_id).first()
    if not post:
        raise HTTPException(status_code=404, detail="Post not found")

    db.delete(post)
    db.commit()
    return RedirectResponse(url="/admin/posts", status_code=303)


@router.get("/settings")
async def edit_settings(
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("admin")),
):
    """Страница настроек сайта"""
    settings = db.query(SiteSettings).first()
    if not settings:
        settings = SiteSettings(theme_colors={})
        db.add(settings)
        db.commit()
        db.refresh(settings)

    return request.app.state.templates.TemplateResponse(
        "admin/settings.html",
        {"request": request, "user": current_user, "settings": settings},
    )


@router.post("/settings")
async def save_settings(
    request: Request,
    site_name: str = Form("Талакан"),
    primary_color: str = Form("#3B82F6"),
    secondary_color: str = Form("#10B981"),
    header_bg: str = Form("#1F2937"),
    banner_url: str = Form(""),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("admin")),
):
    """Сохранение настроек сайта"""
    settings = db.query(SiteSettings).first()
    if not settings:
        settings = SiteSettings()
        db.add(settings)

    settings.site_name = site_name
    settings.theme_colors = {
        "primary": primary_color,
        "secondary": secondary_color,
        "header_bg": header_bg,
        "banner_url": banner_url,
    }
    db.commit()
    return RedirectResponse(url="/admin/settings", status_code=303)


@router.get("/theme")
async def theme_preview(
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("admin")),
):
    """Предпросмотр темы оформления"""
    settings = db.query(SiteSettings).first()
    if not settings:
        settings = SiteSettings(theme_colors={})
        db.add(settings)
        db.commit()
        db.refresh(settings)

    return request.app.state.templates.TemplateResponse(
        "admin/theme_preview.html",
        {"request": request, "user": current_user, "settings": settings},
    )


@router.post("/theme/reset")
async def reset_theme(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("admin")),
):
    """Сброс темы к стандартной"""
    settings = db.query(SiteSettings).first()
    if settings:
        settings.theme_colors = {
            "primary": "#3B82F6",
            "secondary": "#10B981",
            "header_bg": "#1F2937",
            "banner_url": "",
        }
        db.commit()
    return RedirectResponse(url="/admin/settings", status_code=303)


@router.get("/stats")
async def site_stats(
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("admin")),
):
    """Статистика сайта"""
    users_count = db.query(User).count()
    posts_count = db.query(Post).count()
    admins_count = db.query(User).filter(User.role == "admin").count()
    moderators_count = db.query(User).filter(User.role == "moderator").count()

    return request.app.state.templates.TemplateResponse(
        "admin/stats.html",
        {
            "request": request,
            "user": current_user,
            "users_count": users_count,
            "posts_count": posts_count,
            "admins_count": admins_count,
            "moderators_count": moderators_count,
        },
    )
