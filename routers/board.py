# routers/board.py
from fastapi import APIRouter, Request, Depends, HTTPException, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from typing import Dict, Any, Optional
import aiosqlite
from datetime import datetime
from dependencies import templates, get_db, get_theme_settings, get_current_user, get_current_moderator

router = APIRouter()


@router.get("/", response_class=HTMLResponse)
async def board_list(
    request: Request,
    page: int = 1,
    db: aiosqlite.Connection = Depends(get_db),
    theme: Dict[str, str] = Depends(get_theme_settings),
):
    """Список объявлений с пагинацией"""
    per_page = 10
    offset = (page - 1) * per_page

    # Получаем общее количество объявлений
    async with db.execute(
        "SELECT COUNT(*) as count FROM posts WHERE category = 'board' AND is_published = 1"
    ) as cursor:
        total = await cursor.fetchone()
        total_count = total["count"]

    # Получаем объявления с авторами
    async with db.execute(
        """
        SELECT p.*, u.username as author_name 
        FROM posts p 
        JOIN users u ON p.author_id = u.id 
        WHERE p.category = 'board' AND is_published = 1 
        ORDER BY p.created_at DESC 
        LIMIT ? OFFSET ?
        """,
        (per_page, offset),
    ) as cursor:
        board_posts = await cursor.fetchall()

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
        "board.html",
        {
            "request": request,
            "board_posts": board_posts,
            "user": user,
            "theme": theme,
            "current_page": "board",
            "page": page,
            "total_pages": total_pages,
            "total_count": total_count,
        },
    )


@router.get("/create", response_class=HTMLResponse)
async def create_board_form(
    request: Request,
    db: aiosqlite.Connection = Depends(get_db),
    theme: Dict[str, str] = Depends(get_theme_settings),
):
    """Форма создания объявления"""
    user = None
    if "user_id" in request.session:
        async with db.execute(
            "SELECT * FROM users WHERE id = ?", (request.session["user_id"],)
        ) as cursor:
            user_row = await cursor.fetchone()
            if user_row:
                user = dict(user_row)

    if not user:
        return RedirectResponse(url="/auth/login?next=/board/create", status_code=303)

    return templates.TemplateResponse(
        request,
        "board.html",
        {
            "request": request,
            "user": user,
            "theme": theme,
            "current_page": "board",
            "create_mode": True,
        },
    )


@router.post("/create")
async def create_board_post(
    request: Request,
    title: str = Form(...),
    content: str = Form(...),
    db: aiosqlite.Connection = Depends(get_db),
):
    """Создание нового объявления"""
    if "user_id" not in request.session:
        return RedirectResponse(url="/auth/login?next=/board/create", status_code=303)

    user_id = request.session["user_id"]

    # Проверяем, что пользователь существует и активен
    async with db.execute(
        "SELECT * FROM users WHERE id = ? AND is_active = 1", (user_id,)
    ) as cursor:
        user = await cursor.fetchone()

    if not user:
        raise HTTPException(status_code=401, detail="Пользователь не найден")

    # Валидация данных
    if len(title.strip()) < 3:
        raise HTTPException(status_code=400, detail="Заголовок должен быть не менее 3 символов")
    if len(content.strip()) < 10:
        raise HTTPException(status_code=400, detail="Текст должен быть не менее 10 символов")

    # Создаем объявление
    async with db.execute(
        """
        INSERT INTO posts (title, content, category, author_id, is_published, created_at, updated_at)
        VALUES (?, ?, 'board', ?, 1, ?, ?)
        """,
        (title.strip(), content.strip(), user_id, datetime.utcnow(), datetime.utcnow()),
    ) as cursor:
        await db.commit()
        post_id = cursor.lastrowid

    return RedirectResponse(url=f"/board/{post_id}", status_code=303)


@router.get("/{post_id}", response_class=HTMLResponse)
async def board_detail(
    post_id: int,
    request: Request,
    db: aiosqlite.Connection = Depends(get_db),
    theme: Dict[str, str] = Depends(get_theme_settings),
):
    """Детальная страница объявления"""
    async with db.execute(
        """
        SELECT p.*, u.username as author_name, u.email as author_email
        FROM posts p 
        JOIN users u ON p.author_id = u.id 
        WHERE p.id = ? AND p.category = 'board'
        """,
        (post_id,),
    ) as cursor:
        post = await cursor.fetchone()

    if not post:
        raise HTTPException(status_code=404, detail="Объявление не найдено")

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
        "board.html",
        {
            "request": request,
            "post": post,
            "user": user,
            "theme": theme,
            "current_page": "board",
            "detail_mode": True,
        },
    )


@router.get("/{post_id}/edit", response_class=HTMLResponse)
async def edit_board_form(
    post_id: int,
    request: Request,
    db: aiosqlite.Connection = Depends(get_db),
    theme: Dict[str, str] = Depends(get_theme_settings),
):
    """Форма редактирования объявления"""
    if "user_id" not in request.session:
        return RedirectResponse(url=f"/auth/login?next=/board/{post_id}/edit", status_code=303)

    user_id = request.session["user_id"]

    async with db.execute(
        "SELECT * FROM posts WHERE id = ? AND category = 'board'", (post_id,)
    ) as cursor:
        post = await cursor.fetchone()

    if not post:
        raise HTTPException(status_code=404, detail="Объявление не найдено")

    # Проверяем права на редактирование
    if post["author_id"] != user_id:
        # Проверяем, является ли пользователь модератором или админом
        async with db.execute(
            "SELECT role FROM users WHERE id = ?", (user_id,)
        ) as cursor:
            user = await cursor.fetchone()
            if not user or user["role"] not in ["admin", "moderator"]:
                raise HTTPException(status_code=403, detail="Нет прав на редактирование")

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
        "board.html",
        {
            "request": request,
            "post": post,
            "user": user,
            "theme": theme,
            "current_page": "board",
            "edit_mode": True,
        },
    )


@router.post("/{post_id}/edit")
async def edit_board_post(
    post_id: int,
    request: Request,
    title: str = Form(...),
    content: str = Form(...),
    db: aiosqlite.Connection = Depends(get_db),
):
    """Обновление объявления"""
    if "user_id" not in request.session:
        return RedirectResponse(url=f"/auth/login?next=/board/{post_id}/edit", status_code=303)

    user_id = request.session["user_id"]

    async with db.execute(
        "SELECT * FROM posts WHERE id = ? AND category = 'board'", (post_id,)
    ) as cursor:
        post = await cursor.fetchone()

    if not post:
        raise HTTPException(status_code=404, detail="Объявление не найдено")

    # Проверяем права на редактирование
    if post["author_id"] != user_id:
        async with db.execute(
            "SELECT role FROM users WHERE id = ?", (user_id,)
        ) as cursor:
            user = await cursor.fetchone()
            if not user or user["role"] not in ["admin", "moderator"]:
                raise HTTPException(status_code=403, detail="Нет прав на редактирование")

    # Валидация данных
    if len(title.strip()) < 3:
        raise HTTPException(status_code=400, detail="Заголовок должен быть не менее 3 символов")
    if len(content.strip()) < 10:
        raise HTTPException(status_code=400, detail="Текст должен быть не менее 10 символов")

    # Обновляем объявление
    async with db.execute(
        """
        UPDATE posts 
        SET title = ?, content = ?, updated_at = ?
        WHERE id = ?
        """,
        (title.strip(), content.strip(), datetime.utcnow(), post_id),
    ):
        await db.commit()

    return RedirectResponse(url=f"/board/{post_id}", status_code=303)


@router.post("/{post_id}/delete")
async def delete_board_post(
    post_id: int,
    request: Request,
    db: aiosqlite.Connection = Depends(get_db),
):
    """Удаление объявления"""
    if "user_id" not in request.session:
        return RedirectResponse(url="/auth/login", status_code=303)

    user_id = request.session["user_id"]

    async with db.execute(
        "SELECT * FROM posts WHERE id = ? AND category = 'board'", (post_id,)
    ) as cursor:
        post = await cursor.fetchone()

    if not post:
        raise HTTPException(status_code=404, detail="Объявление не найдено")

    # Проверяем права на удаление
    if post["author_id"] != user_id:
        async with db.execute(
            "SELECT role FROM users WHERE id = ?", (user_id,)
        ) as cursor:
            user = await cursor.fetchone()
            if not user or user["role"] not in ["admin", "moderator"]:
                raise HTTPException(status_code=403, detail="Нет прав на удаление")

    # Удаляем объявление
    async with db.execute("DELETE FROM posts WHERE id = ?", (post_id,)):
        await db.commit()

    return RedirectResponse(url="/board", status_code=303)


@router.get("/api/board/posts")
async def get_board_posts(
    page: int = 1,
    per_page: int = 10,
    db: aiosqlite.Connection = Depends(get_db),
):
    """API для получения списка объявлений"""
    offset = (page - 1) * per_page

    async with db.execute(
        """
        SELECT p.*, u.username as author_name 
        FROM posts p 
        JOIN users u ON p.author_id = u.id 
        WHERE p.category = 'board' AND p.is_published = 1 
        ORDER BY p.created_at DESC 
        LIMIT ? OFFSET ?
        """,
        (per_page, offset),
    ) as cursor:
        posts = await cursor.fetchall()

    async with db.execute(
        "SELECT COUNT(*) as count FROM posts WHERE category = 'board' AND is_published = 1"
    ) as cursor:
        total = await cursor.fetchone()

    return {
        "posts": [dict(post) for post in posts],
        "total": total["count"],
        "page": page,
        "per_page": per_page,
    }
