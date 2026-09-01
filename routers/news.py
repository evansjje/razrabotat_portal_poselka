# routers/news.py
from fastapi import APIRouter, Request, Depends, HTTPException, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from typing import Dict, Any, Optional
import aiosqlite
from datetime import datetime
from dependencies import templates, get_db, get_theme_settings, get_current_user, get_current_moderator

router = APIRouter()


@router.get("/", response_class=HTMLResponse)
async def news_list(
    request: Request,
    page: int = 1,
    db: aiosqlite.Connection = Depends(get_db),
    theme: Dict[str, str] = Depends(get_theme_settings),
):
    """Список новостей с пагинацией"""
    per_page = 10
    offset = (page - 1) * per_page

    # Получаем общее количество новостей
    async with db.execute(
        "SELECT COUNT(*) as count FROM posts WHERE category = 'news' AND is_published = 1"
    ) as cursor:
        total = await cursor.fetchone()
        total_count = total["count"]

    # Получаем новости с авторами
    async with db.execute(
        """
        SELECT p.*, u.username as author_name 
        FROM posts p 
        JOIN users u ON p.author_id = u.id 
        WHERE p.category = 'news' AND p.is_published = 1 
        ORDER BY p.created_at DESC 
        LIMIT ? OFFSET ?
        """,
        (per_page, offset),
    ) as cursor:
        news = await cursor.fetchall()

    # Получаем текущего пользователя
    user = None
    if "user_id" in request.session:
        async with db.execute(
            "SELECT * FROM users WHERE id = ?", (request.session["user_id"],)
        ) as cursor:
            user_row = await cursor.fetchone()
            if user_row:
                user = dict(user_row)

    total_pages = (total_count + per_page - 1) // per_page

    return templates.TemplateResponse(
        request,
        "news.html",
        {
            "request": request,
            "news": news,
            "user": user,
            "theme": theme,
            "current_page": "news",
            "page": page,
            "total_pages": total_pages,
            "total_count": total_count,
        },
    )


@router.get("/{news_id}", response_class=HTMLResponse)
async def news_detail(
    news_id: int,
    request: Request,
    db: aiosqlite.Connection = Depends(get_db),
    theme: Dict[str, str] = Depends(get_theme_settings),
):
    """Детальная страница новости"""
    async with db.execute(
        """
        SELECT p.*, u.username as author_name, u.email as author_email
        FROM posts p 
        JOIN users u ON p.author_id = u.id 
        WHERE p.id = ? AND p.category = 'news' AND p.is_published = 1
        """,
        (news_id,),
    ) as cursor:
        news = await cursor.fetchone()

    if not news:
        raise HTTPException(status_code=404, detail="Новость не найдена")

    # Получаем текущего пользователя
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
        "news_detail.html",
        {
            "request": request,
            "news": news,
            "user": user,
            "theme": theme,
            "current_page": "news",
        },
    )


@router.post("/create", response_class=HTMLResponse)
async def create_news(
    request: Request,
    title: str = Form(...),
    content: str = Form(...),
    db: aiosqlite.Connection = Depends(get_db),
    theme: Dict[str, str] = Depends(get_theme_settings),
):
    """Создание новости (только для модераторов и админов)"""
    # Проверяем авторизацию
    if "user_id" not in request.session:
        return RedirectResponse(url="/auth/login", status_code=303)

    # Получаем пользователя
    async with db.execute(
        "SELECT * FROM users WHERE id = ?", (request.session["user_id"],)
    ) as cursor:
        user = await cursor.fetchone()

    if not user or user["role"] not in ["admin", "moderator"]:
        raise HTTPException(status_code=403, detail="Недостаточно прав")

    # Создаем новость
    async with db.execute(
        """
        INSERT INTO posts (title, content, category, author_id, is_published, created_at, updated_at)
        VALUES (?, ?, 'news', ?, 1, ?, ?)
        """,
        (title, content, user["id"], datetime.now(), datetime.now()),
    ) as cursor:
        await db.commit()
        news_id = cursor.lastrowid

    return RedirectResponse(url=f"/news/{news_id}", status_code=303)


@router.post("/{news_id}/delete")
async def delete_news(
    news_id: int,
    request: Request,
    db: aiosqlite.Connection = Depends(get_db),
):
    """Удаление новости (только для модераторов и админов)"""
    # Проверяем авторизацию
    if "user_id" not in request.session:
        return RedirectResponse(url="/auth/login", status_code=303)

    # Получаем пользователя
    async with db.execute(
        "SELECT * FROM users WHERE id = ?", (request.session["user_id"],)
    ) as cursor:
        user = await cursor.fetchone()

    if not user or user["role"] not in ["admin", "moderator"]:
        raise HTTPException(status_code=403, detail="Недостаточно прав")

    # Проверяем существование новости
    async with db.execute(
        "SELECT * FROM posts WHERE id = ? AND category = 'news'", (news_id,)
    ) as cursor:
        news = await cursor.fetchone()

    if not news:
        raise HTTPException(status_code=404, detail="Новость не найдена")

    # Удаляем новость
    await db.execute("DELETE FROM posts WHERE id = ?", (news_id,))
    await db.commit()

    return RedirectResponse(url="/news", status_code=303)


@router.get("/api/news")
async def get_news_api(
    db: aiosqlite.Connection = Depends(get_db),
    limit: int = 10,
    offset: int = 0,
):
    """API для получения новостей"""
    async with db.execute(
        """
        SELECT p.*, u.username as author_name 
        FROM posts p 
        JOIN users u ON p.author_id = u.id 
        WHERE p.category = 'news' AND p.is_published = 1 
        ORDER BY p.created_at DESC 
        LIMIT ? OFFSET ?
        """,
        (limit, offset),
    ) as cursor:
        news = await cursor.fetchall()

    return [dict(row) for row in news]


@router.get("/api/news/{news_id}")
async def get_news_detail_api(
    news_id: int,
    db: aiosqlite.Connection = Depends(get_db),
):
    """API для получения конкретной новости"""
    async with db.execute(
        """
        SELECT p.*, u.username as author_name 
        FROM posts p 
        JOIN users u ON p.author_id = u.id 
        WHERE p.id = ? AND p.category = 'news' AND p.is_published = 1
        """,
        (news_id,),
    ) as cursor:
        news = await cursor.fetchone()

    if not news:
        raise HTTPException(status_code=404, detail="Новость не найдена")

    return dict(news)
