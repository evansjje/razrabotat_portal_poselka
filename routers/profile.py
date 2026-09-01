# routers/profile.py
from fastapi import APIRouter, Request, Depends, HTTPException, Form, UploadFile, File
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
from typing import Dict, Any, Optional
import aiosqlite
from datetime import datetime
import os
import shutil
from dependencies import templates, get_db, get_theme_settings, get_current_user
from auth import get_password_hash, verify_password
from config import settings

router = APIRouter()


@router.get("/", response_class=HTMLResponse)
async def profile_page(
    request: Request,
    db: aiosqlite.Connection = Depends(get_db),
    theme: Dict[str, str] = Depends(get_theme_settings),
):
    """Личный кабинет пользователя"""
    user = None
    if "user_id" in request.session:
        async with db.execute(
            "SELECT * FROM users WHERE id = ?", (request.session["user_id"],)
        ) as cursor:
            user_row = await cursor.fetchone()
            if user_row:
                user = dict(user_row)
    
    if user is None:
        return RedirectResponse(url="/auth/login", status_code=302)

    # Получаем посты пользователя
    async with db.execute(
        """
        SELECT * FROM posts 
        WHERE author_id = ? 
        ORDER BY created_at DESC 
        LIMIT 20
        """,
        (user["id"],),
    ) as cursor:
        user_posts = await cursor.fetchall()

    return templates.TemplateResponse(
        request,
        "profile.html",
        {
            "request": request,
            "user": user,
            "theme": theme,
            "current_page": "profile",
            "user_posts": user_posts,
            "success_message": request.query_params.get("success"),
            "error_message": request.query_params.get("error"),
        },
    )


@router.post("/update", response_class=HTMLResponse)
async def update_profile(
    request: Request,
    username: str = Form(...),
    email: str = Form(...),
    phone: Optional[str] = Form(None),
    current_password: Optional[str] = Form(None),
    new_password: Optional[str] = Form(None),
    db: aiosqlite.Connection = Depends(get_db),
):
    """Обновление профиля пользователя"""
    if "user_id" not in request.session:
        return RedirectResponse(url="/auth/login", status_code=302)

    user_id = request.session["user_id"]

    # Проверяем уникальность username
    async with db.execute(
        "SELECT id FROM users WHERE username = ? AND id != ?",
        (username, user_id),
    ) as cursor:
        existing = await cursor.fetchone()
        if existing:
            return RedirectResponse(
                url="/profile?error=Имя пользователя уже занято", status_code=302
            )

    # Проверяем уникальность email
    async with db.execute(
        "SELECT id FROM users WHERE email = ? AND id != ?",
        (email, user_id),
    ) as cursor:
        existing = await cursor.fetchone()
        if existing:
            return RedirectResponse(
                url="/profile?error=Email уже используется", status_code=302
            )

    # Получаем текущего пользователя
    async with db.execute("SELECT * FROM users WHERE id = ?", (user_id,)) as cursor:
        user_row = await cursor.fetchone()
        if user_row is None:
            return RedirectResponse(url="/auth/login", status_code=302)
        user = dict(user_row)

    # Если указан новый пароль, проверяем текущий
    if new_password:
        if not current_password or not verify_password(current_password, user["hashed_password"]):
            return RedirectResponse(
                url="/profile?error=Неверный текущий пароль", status_code=302
            )
        if len(new_password) < 6:
            return RedirectResponse(
                url="/profile?error=Новый пароль должен быть не менее 6 символов", status_code=302
            )

    # Обновляем данные
    try:
        if new_password:
            hashed_password = get_password_hash(new_password)
            await db.execute(
                """
                UPDATE users 
                SET username = ?, email = ?, phone = ?, hashed_password = ?, updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
                """,
                (username, email, phone, hashed_password, user_id),
            )
        else:
            await db.execute(
                """
                UPDATE users 
                SET username = ?, email = ?, phone = ?, updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
                """,
                (username, email, phone, user_id),
            )
        await db.commit()
        return RedirectResponse(url="/profile?success=Профиль успешно обновлен", status_code=302)
    except Exception as e:
        return RedirectResponse(
            url=f"/profile?error=Ошибка при обновлении: {str(e)}", status_code=302
        )


@router.post("/avatar", response_class=HTMLResponse)
async def upload_avatar(
    request: Request,
    avatar: UploadFile = File(...),
    db: aiosqlite.Connection = Depends(get_db),
):
    """Загрузка аватара пользователя"""
    if "user_id" not in request.session:
        return RedirectResponse(url="/auth/login", status_code=302)

    user_id = request.session["user_id"]

    # Проверяем расширение файла
    ext = avatar.filename.split(".")[-1].lower() if "." in avatar.filename else ""
    if ext not in settings.ALLOWED_EXTENSIONS:
        return RedirectResponse(
            url="/profile?error=Недопустимый формат файла", status_code=302
        )

    # Проверяем размер файла
    content = await avatar.read()
    if len(content) > settings.MAX_UPLOAD_SIZE:
        return RedirectResponse(
            url="/profile?error=Файл слишком большой (макс. 5MB)", status_code=302
        )

    # Создаем директорию для аватаров
    avatar_dir = os.path.join(settings.STATIC_DIR, "uploads", "avatars")
    os.makedirs(avatar_dir, exist_ok=True)

    # Сохраняем файл
    filename = f"avatar_{user_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.{ext}"
    file_path = os.path.join(avatar_dir, filename)

    with open(file_path, "wb") as f:
        f.write(content)

    # Обновляем путь к аватару в БД
    avatar_url = f"/static/uploads/avatars/{filename}"
    await db.execute(
        "UPDATE users SET avatar_url = ? WHERE id = ?",
        (avatar_url, user_id),
    )
    await db.commit()

    return RedirectResponse(url="/profile?success=Аватар успешно загружен", status_code=302)


@router.get("/my-posts", response_class=HTMLResponse)
async def my_posts(
    request: Request,
    db: aiosqlite.Connection = Depends(get_db),
    theme: Dict[str, str] = Depends(get_theme_settings),
):
    """Мои публикации"""
    user = None
    if "user_id" in request.session:
        async with db.execute(
            "SELECT * FROM users WHERE id = ?", (request.session["user_id"],)
        ) as cursor:
            user_row = await cursor.fetchone()
            if user_row:
                user = dict(user_row)

    if user is None:
        return RedirectResponse(url="/auth/login", status_code=302)

    # Получаем все посты пользователя
    async with db.execute(
        """
        SELECT p.*, 
               CASE WHEN p.category = 'news' THEN 'Новость' ELSE 'Объявление' END as category_name
        FROM posts p
        WHERE p.author_id = ?
        ORDER BY p.created_at DESC
        """,
        (user["id"],),
    ) as cursor:
        posts = await cursor.fetchall()

    return templates.TemplateResponse(
        request,
        "profile.html",
        {
            "request": request,
            "user": user,
            "theme": theme,
            "current_page": "profile",
            "user_posts": posts,
            "active_tab": "posts",
        },
    )


@router.post("/delete-post/{post_id}")
async def delete_post(
    post_id: int,
    request: Request,
    db: aiosqlite.Connection = Depends(get_db),
):
    """Удаление своего поста"""
    if "user_id" not in request.session:
        return RedirectResponse(url="/auth/login", status_code=302)

    user_id = request.session["user_id"]

    # Проверяем, что пост принадлежит пользователю
    async with db.execute(
        "SELECT * FROM posts WHERE id = ? AND author_id = ?",
        (post_id, user_id),
    ) as cursor:
        post = await cursor.fetchone()

    if post is None:
        return RedirectResponse(
            url="/profile?error=Пост не найден или нет прав на удаление", status_code=302
        )

    # Удаляем пост
    await db.execute("DELETE FROM posts WHERE id = ?", (post_id,))
    await db.commit()

    return RedirectResponse(url="/profile?success=Пост успешно удален", status_code=302)


@router.get("/settings", response_class=HTMLResponse)
async def profile_settings(
    request: Request,
    db: aiosqlite.Connection = Depends(get_db),
    theme: Dict[str, str] = Depends(get_theme_settings),
):
    """Настройки профиля"""
    user = None
    if "user_id" in request.session:
        async with db.execute(
            "SELECT * FROM users WHERE id = ?", (request.session["user_id"],)
        ) as cursor:
            user_row = await cursor.fetchone()
            if user_row:
                user = dict(user_row)

    if user is None:
        return RedirectResponse(url="/auth/login", status_code=302)

    return templates.TemplateResponse(
        request,
        "profile.html",
        {
            "request": request,
            "user": user,
            "theme": theme,
            "current_page": "profile",
            "active_tab": "settings",
        },
    )


@router.post("/change-password")
async def change_password(
    request: Request,
    current_password: str = Form(...),
    new_password: str = Form(...),
    confirm_password: str = Form(...),
    db: aiosqlite.Connection = Depends(get_db),
):
    """Смена пароля"""
    if "user_id" not in request.session:
        return RedirectResponse(url="/auth/login", status_code=302)

    user_id = request.session["user_id"]

    # Получаем пользователя
    async with db.execute("SELECT * FROM users WHERE id = ?", (user_id,)) as cursor:
        user_row = await cursor.fetchone()
        if user_row is None:
            return RedirectResponse(url="/auth/login", status_code=302)
        user = dict(user_row)

    # Проверяем текущий пароль
    if not verify_password(current_password, user["hashed_password"]):
        return RedirectResponse(
            url="/profile?error=Неверный текущий пароль", status_code=302
        )

    # Проверяем совпадение новых паролей
    if new_password != confirm_password:
        return RedirectResponse(
            url="/profile?error=Пароли не совпадают", status_code=302
        )

    # Проверяем длину пароля
    if len(new_password) < 6:
        return RedirectResponse(
            url="/profile?error=Пароль должен быть не менее 6 символов", status_code=302
        )

    # Обновляем пароль
    hashed_password = get_password_hash(new_password)
    await db.execute(
        "UPDATE users SET hashed_password = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
        (hashed_password, user_id),
    )
    await db.commit()

    return RedirectResponse(url="/profile?success=Пароль успешно изменен", status_code=302)


@router.get("/api/profile/stats")
async def get_profile_stats(
    request: Request,
    db: aiosqlite.Connection = Depends(get_db),
):
    """API для получения статистики профиля"""
    if "user_id" not in request.session:
        return JSONResponse({"error": "Not authenticated"}, status_code=401)

    user_id = request.session["user_id"]

    stats = {}

    # Количество постов
    async with db.execute(
        "SELECT COUNT(*) as count FROM posts WHERE author_id = ?",
        (user_id,),
    ) as cursor:
        row = await cursor.fetchone()
        stats["total_posts"] = row["count"]

    # Количество новостей
    async with db.execute(
        "SELECT COUNT(*) as count FROM posts WHERE author_id = ? AND category = 'news'",
        (user_id,),
    ) as cursor:
        row = await cursor.fetchone()
        stats["news_count"] = row["count"]

    # Количество объявлений
    async with db.execute(
        "SELECT COUNT(*) as count FROM posts WHERE author_id = ? AND category = 'board'",
        (user_id,),
    ) as cursor:
        row = await cursor.fetchone()
        stats["board_count"] = row["count"]

    # Дата регистрации
    async with db.execute(
        "SELECT created_at FROM users WHERE id = ?",
        (user_id,),
    ) as cursor:
        row = await cursor.fetchone()
        stats["registered_at"] = row["created_at"] if row else None

    return JSONResponse(stats)
