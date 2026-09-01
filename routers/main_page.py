# routers/main_page.py
from fastapi import APIRouter, Request, Depends
from fastapi.responses import HTMLResponse
from typing import Dict, Any
import aiosqlite
from dependencies import templates, get_db, get_theme_settings

router = APIRouter()


@router.get("/", response_class=HTMLResponse)
async def main_page(
    request: Request,
    db: aiosqlite.Connection = Depends(get_db),
    theme: Dict[str, str] = Depends(get_theme_settings),
):
    """Главная страница портала"""
    # Получаем последние новости
    async with db.execute(
        """
        SELECT p.*, u.username as author_name 
        FROM posts p 
        JOIN users u ON p.author_id = u.id 
        WHERE p.category = 'news' AND p.is_published = 1 
        ORDER BY p.created_at DESC 
        LIMIT 5
        """
    ) as cursor:
        news = await cursor.fetchall()

    # Получаем последние объявления
    async with db.execute(
        """
        SELECT p.*, u.username as author_name 
        FROM posts p 
        JOIN users u ON p.author_id = u.id 
        WHERE p.category = 'board' AND p.is_published = 1 
        ORDER BY p.created_at DESC 
        LIMIT 5
        """
    ) as cursor:
        board_posts = await cursor.fetchall()

    # Получаем текущего пользователя из сессии
    user = None
    if "user_id" in request.session:
        async with db.execute(
            "SELECT * FROM users WHERE id = ?", (request.session["user_id"],)
        ) as cursor:
            user_row = await cursor.fetchone()
            if user_row:
                user = dict(user_row)

    return templates.TemplateResponse(
        request,
        "index.html",
        {
            "request": request,
            "news": news,
            "board_posts": board_posts,
            "user": user,
            "theme": theme,
            "current_page": "main",
        },
    )


@router.get("/health")
async def health_check():
    """Проверка работоспособности сервиса"""
    return {"status": "ok"}


@router.get("/api/main/stats")
async def get_stats(db: aiosqlite.Connection = Depends(get_db)):
    """Получение статистики портала"""
    stats = {}

    # Количество пользователей
    async with db.execute("SELECT COUNT(*) as count FROM users") as cursor:
        row = await cursor.fetchone()
        stats["users"] = row["count"]

    # Количество новостей
    async with db.execute(
        "SELECT COUNT(*) as count FROM posts WHERE category = 'news'"
    ) as cursor:
        row = await cursor.fetchone()
        stats["news"] = row["count"]

    # Количество объявлений
    async with db.execute(
        "SELECT COUNT(*) as count FROM posts WHERE category = 'board'"
    ) as cursor:
        row = await cursor.fetchone()
        stats["board"] = row["count"]

    return stats


@router.get("/api/main/latest")
async def get_latest_posts(db: aiosqlite.Connection = Depends(get_db)):
    """Получение последних постов для AJAX обновления"""
    async with db.execute(
        """
        SELECT p.*, u.username as author_name 
        FROM posts p 
        JOIN users u ON p.author_id = u.id 
        WHERE p.is_published = 1 
        ORDER BY p.created_at DESC 
        LIMIT 10
        """
    ) as cursor:
        posts = await cursor.fetchall()

    return [dict(post) for post in posts]


@router.get("/api/main/theme")
async def get_theme(theme: Dict[str, str] = Depends(get_theme_settings)):
    """Получение текущей темы оформления"""
    return theme


@router.get("/api/main/search")
async def search_posts(
    q: str,
    db: aiosqlite.Connection = Depends(get_db),
):
    """Поиск по постам"""
    search_term = f"%{q}%"
    async with db.execute(
        """
        SELECT p.*, u.username as author_name 
        FROM posts p 
        JOIN users u ON p.author_id = u.id 
        WHERE p.is_published = 1 
        AND (p.title LIKE ? OR p.content LIKE ?)
        ORDER BY p.created_at DESC 
        LIMIT 20
        """,
        (search_term, search_term),
    ) as cursor:
        posts = await cursor.fetchall()

    return [dict(post) for post in posts]


@router.get("/api/main/weather")
async def get_weather_data():
    """Получение данных о погоде (заглушка для API)"""
    # Здесь можно интегрировать реальный API погоды
    return {
        "city": "Талакан",
        "temperature": -5,
        "condition": "ясно",
        "humidity": 65,
        "wind_speed": 3.5,
        "updated_at": "2024-01-15 12:00:00"
    }
