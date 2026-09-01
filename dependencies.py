# dependencies.py
from fastapi import Depends, HTTPException, status
from fastapi.templating import Jinja2Templates
from typing import AsyncGenerator, Optional, Dict, Any
import aiosqlite
from config import settings
from auth import get_current_user as auth_get_current_user

# Templates instance
templates = Jinja2Templates(directory=settings.TEMPLATES_DIR)

async def get_db() -> AsyncGenerator[aiosqlite.Connection, None]:
    """Get database connection"""
    db_path = settings.DATABASE_URL.replace("sqlite:///", "")
    db = await aiosqlite.connect(db_path)
    db.row_factory = aiosqlite.Row
    try:
        yield db
    finally:
        await db.close()

async def get_current_user(
    db: aiosqlite.Connection = Depends(get_db),
    token: str = Depends(auth_get_current_user)
) -> Dict[str, Any]:
    """Get current user from database"""
    if isinstance(token, dict):
        return token
    
    async with db.execute(
        "SELECT * FROM users WHERE id = ?", (token["id"],)
    ) as cursor:
        user = await cursor.fetchone()
    
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found"
        )
    return dict(user)

async def get_current_admin(
    current_user: Dict[str, Any] = Depends(get_current_user)
) -> Dict[str, Any]:
    """Check if current user is admin"""
    if current_user["role"] != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions"
        )
    return current_user

async def get_current_moderator(
    current_user: Dict[str, Any] = Depends(get_current_user)
) -> Dict[str, Any]:
    """Check if current user is moderator or admin"""
    if current_user["role"] not in ["admin", "moderator"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions"
        )
    return current_user

async def get_theme_settings(db: aiosqlite.Connection = Depends(get_db)) -> Dict[str, str]:
    """Get current theme settings"""
    async with db.execute("SELECT * FROM themes ORDER BY id DESC LIMIT 1") as cursor:
        theme = await cursor.fetchone()
    
    if theme is None:
        return settings.DEFAULT_THEME
    
    return {
        "primary_color": theme["primary_color"],
        "secondary_color": theme["secondary_color"],
        "header_bg": theme["header_bg"],
        "header_text": theme["header_text"],
        "button_bg": theme["button_bg"],
        "button_text": theme["button_text"],
        "banner_url": theme["banner_url"],
        "footer_bg": theme["footer_bg"],
        "footer_text": theme["footer_text"]
    }

async def get_site_settings(db: aiosqlite.Connection = Depends(get_db)) -> Dict[str, str]:
    """Get site settings"""
    settings_dict = {}
    async with db.execute("SELECT key, value FROM settings") as cursor:
        rows = await cursor.fetchall()
        for row in rows:
            settings_dict[row["key"]] = row["value"]
    return settings_dict

def get_template_context(
    request,
    theme: Dict[str, str] = None,
    site_settings: Dict[str, str] = None,
    **kwargs
) -> Dict[str, Any]:
    """Create template context with common variables"""
    context = {
        "request": request,
        "app_name": settings.APP_NAME,
        "app_version": settings.APP_VERSION,
        "debug": settings.DEBUG,
    }
    
    if theme:
        context["theme"] = theme
    else:
        context["theme"] = settings.DEFAULT_THEME
    
    if site_settings:
        context["site_settings"] = site_settings
    
    context.update(kwargs)
    return context

async def get_paginated_posts(
    db: aiosqlite.Connection,
    category: str = None,
    page: int = 1,
    per_page: int = 10
) -> Dict[str, Any]:
    """Get paginated posts"""
    offset = (page - 1) * per_page
    
    if category:
        query = "SELECT * FROM posts WHERE category = ? AND is_published = 1 ORDER BY created_at DESC LIMIT ? OFFSET ?"
        params = (category, per_page, offset)
        count_query = "SELECT COUNT(*) as count FROM posts WHERE category = ? AND is_published = 1"
        count_params = (category,)
    else:
        query = "SELECT * FROM posts WHERE is_published = 1 ORDER BY created_at DESC LIMIT ? OFFSET ?"
        params = (per_page, offset)
        count_query = "SELECT COUNT(*) as count FROM posts WHERE is_published = 1"
        count_params = ()
    
    async with db.execute(query, params) as cursor:
        posts = await cursor.fetchall()
    
    async with db.execute(count_query, count_params) as cursor:
        result = await cursor.fetchone()
        total = result["count"] if result else 0
    
    return {
        "posts": [dict(post) for post in posts],
        "total": total,
        "page": page,
        "per_page": per_page,
        "total_pages": (total + per_page - 1) // per_page
    }

async def get_user_posts(
    db: aiosqlite.Connection,
    user_id: int,
    page: int = 1,
    per_page: int = 10
) -> Dict[str, Any]:
    """Get user's posts with pagination"""
    offset = (page - 1) * per_page
    
    async with db.execute(
        "SELECT * FROM posts WHERE author_id = ? ORDER BY created_at DESC LIMIT ? OFFSET ?",
        (user_id, per_page, offset)
    ) as cursor:
        posts = await cursor.fetchall()
    
    async with db.execute(
        "SELECT COUNT(*) as count FROM posts WHERE author_id = ?",
        (user_id,)
    ) as cursor:
        result = await cursor.fetchone()
        total = result["count"] if result else 0
    
    return {
        "posts": [dict(post) for post in posts],
        "total": total,
        "page": page,
        "per_page": per_page,
        "total_pages": (total + per_page - 1) // per_page
    }

async def get_weather_data() -> Optional[Dict[str, Any]]:
    """Get weather data for Talakan"""
    try:
        import httpx
        from services.weather_service import get_weather
        
        weather = await get_weather()
        return weather
    except Exception:
        return None

async def get_recent_posts(
    db: aiosqlite.Connection,
    limit: int = 5
) -> list:
    """Get recent posts"""
    async with db.execute(
        "SELECT * FROM posts WHERE is_published = 1 ORDER BY created_at DESC LIMIT ?",
        (limit,)
    ) as cursor:
        posts = await cursor.fetchall()
    return [dict(post) for post in posts]

async def get_user_stats(
    db: aiosqlite.Connection,
    user_id: int
) -> Dict[str, int]:
    """Get user statistics"""
    async with db.execute(
        "SELECT COUNT(*) as total FROM posts WHERE author_id = ?",
        (user_id,)
    ) as cursor:
        result = await cursor.fetchone()
        total_posts = result["total"] if result else 0
    
    async with db.execute(
        "SELECT COUNT(*) as total FROM posts WHERE author_id = ? AND category = 'news'",
        (user_id,)
    ) as cursor:
        result = await cursor.fetchone()
        news_posts = result["total"] if result else 0
    
    async with db.execute(
        "SELECT COUNT(*) as total FROM posts WHERE author_id = ? AND category = 'board'",
        (user_id,)
    ) as cursor:
        result = await cursor.fetchone()
        board_posts = result["total"] if result else 0
    
    return {
        "total_posts": total_posts,
        "news_posts": news_posts,
        "board_posts": board_posts
    }

async def check_permission(
    current_user: Dict[str, Any],
    post_author_id: int
) -> bool:
    """Check if user can modify post"""
    if current_user["role"] == "admin":
        return True
    if current_user["role"] == "moderator":
        return True
    return current_user["id"] == post_author_id

def validate_file_extension(filename: str) -> bool:
    """Validate file extension"""
    ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
    return ext in settings.ALLOWED_EXTENSIONS

async def save_upload_file(upload_file, destination: str) -> str:
    """Save uploaded file"""
    import shutil
    import os
    
    os.makedirs(os.path.dirname(destination), exist_ok=True)
    
    with open(destination, "wb") as buffer:
        shutil.copyfileobj(upload_file.file, buffer)
    
    return destination
