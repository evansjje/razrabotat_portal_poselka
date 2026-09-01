# routers/auth.py
from fastapi import APIRouter, Request, Depends, HTTPException, Form, status
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
from fastapi.security import OAuth2PasswordRequestForm
from typing import Dict, Any, Optional
import aiosqlite
from datetime import datetime
from dependencies import templates, get_db, get_theme_settings
from auth import get_password_hash, verify_password, create_access_token
from models import UserRole

router = APIRouter()


@router.get("/login", response_class=HTMLResponse)
async def login_page(
    request: Request,
    db: aiosqlite.Connection = Depends(get_db),
    theme: Dict[str, str] = Depends(get_theme_settings),
):
    """Страница входа"""
    user = None
    if "user_id" in request.session:
        async with db.execute(
            "SELECT * FROM users WHERE id = ?", (request.session["user_id"],)
        ) as cursor:
            user_row = await cursor.fetchone()
            if user_row:
                user = dict(user_row)
                return RedirectResponse(url="/profile", status_code=302)

    return templates.TemplateResponse(
        request,
        "login.html",
        {
            "request": request,
            "user": user,
            "theme": theme,
            "current_page": "login",
            "error": None,
        },
    )


@router.post("/login", response_class=HTMLResponse)
async def login_submit(
    request: Request,
    email: str = Form(...),
    password: str = Form(...),
    db: aiosqlite.Connection = Depends(get_db),
    theme: Dict[str, str] = Depends(get_theme_settings),
):
    """Обработка входа"""
    # Ищем пользователя по email
    async with db.execute("SELECT * FROM users WHERE email = ?", (email,)) as cursor:
        user_row = await cursor.fetchone()

    if user_row is None:
        return templates.TemplateResponse(
            request,
            "login.html",
            {
                "request": request,
                "user": None,
                "theme": theme,
                "current_page": "login",
                "error": "Пользователь с таким email не найден",
            },
            status_code=400,
        )

    user = dict(user_row)

    # Проверяем пароль
    if not verify_password(password, user["hashed_password"]):
        return templates.TemplateResponse(
            request,
            "login.html",
            {
                "request": request,
                "user": None,
                "theme": theme,
                "current_page": "login",
                "error": "Неверный пароль",
            },
            status_code=400,
        )

    # Проверяем активность пользователя
    if not user["is_active"]:
        return templates.TemplateResponse(
            request,
            "login.html",
            {
                "request": request,
                "user": None,
                "theme": theme,
                "current_page": "login",
                "error": "Аккаунт заблокирован. Обратитесь к администратору",
            },
            status_code=403,
        )

    # Создаем сессию
    request.session["user_id"] = user["id"]
    request.session["user_role"] = user["role"]

    return RedirectResponse(url="/profile", status_code=302)


@router.get("/register", response_class=HTMLResponse)
async def register_page(
    request: Request,
    db: aiosqlite.Connection = Depends(get_db),
    theme: Dict[str, str] = Depends(get_theme_settings),
):
    """Страница регистрации"""
    user = None
    if "user_id" in request.session:
        async with db.execute(
            "SELECT * FROM users WHERE id = ?", (request.session["user_id"],)
        ) as cursor:
            user_row = await cursor.fetchone()
            if user_row:
                user = dict(user_row)
                return RedirectResponse(url="/profile", status_code=302)

    return templates.TemplateResponse(
        request,
        "register.html",
        {
            "request": request,
            "user": user,
            "theme": theme,
            "current_page": "register",
            "error": None,
        },
    )


@router.post("/register", response_class=HTMLResponse)
async def register_submit(
    request: Request,
    email: str = Form(...),
    phone: str = Form(""),
    username: str = Form(...),
    password: str = Form(...),
    password_confirm: str = Form(...),
    db: aiosqlite.Connection = Depends(get_db),
    theme: Dict[str, str] = Depends(get_theme_settings),
):
    """Обработка регистрации"""
    # Проверяем совпадение паролей
    if password != password_confirm:
        return templates.TemplateResponse(
            request,
            "register.html",
            {
                "request": request,
                "user": None,
                "theme": theme,
                "current_page": "register",
                "error": "Пароли не совпадают",
            },
            status_code=400,
        )

    # Проверяем минимальную длину пароля
    if len(password) < 6:
        return templates.TemplateResponse(
            request,
            "register.html",
            {
                "request": request,
                "user": None,
                "theme": theme,
                "current_page": "register",
                "error": "Пароль должен содержать минимум 6 символов",
            },
            status_code=400,
        )

    # Проверяем уникальность email
    async with db.execute("SELECT id FROM users WHERE email = ?", (email,)) as cursor:
        if await cursor.fetchone():
            return templates.TemplateResponse(
                request,
                "register.html",
                {
                    "request": request,
                    "user": None,
                    "theme": theme,
                    "current_page": "register",
                    "error": "Пользователь с таким email уже существует",
                },
                status_code=400,
            )

    # Проверяем уникальность username
    async with db.execute("SELECT id FROM users WHERE username = ?", (username,)) as cursor:
        if await cursor.fetchone():
            return templates.TemplateResponse(
                request,
                "register.html",
                {
                    "request": request,
                    "user": None,
                    "theme": theme,
                    "current_page": "register",
                    "error": "Пользователь с таким именем уже существует",
                },
                status_code=400,
            )

    # Проверяем уникальность телефона (если указан)
    if phone:
        async with db.execute("SELECT id FROM users WHERE phone = ?", (phone,)) as cursor:
            if await cursor.fetchone():
                return templates.TemplateResponse(
                    request,
                    "register.html",
                    {
                        "request": request,
                        "user": None,
                        "theme": theme,
                        "current_page": "register",
                        "error": "Пользователь с таким телефоном уже существует",
                    },
                    status_code=400,
                )

    # Хешируем пароль
    hashed_password = get_password_hash(password)

    # Определяем роль (первый пользователь - админ)
    async with db.execute("SELECT COUNT(*) as count FROM users") as cursor:
        count_row = await cursor.fetchone()
        role = UserRole.ADMIN.value if count_row["count"] == 0 else UserRole.USER.value

    # Создаем пользователя
    async with db.execute(
        """
        INSERT INTO users (email, phone, username, hashed_password, role, is_active, created_at, updated_at)
        VALUES (?, ?, ?, ?, ?, 1, ?, ?)
        """,
        (email, phone or None, username, hashed_password, role, datetime.utcnow(), datetime.utcnow()),
    ) as cursor:
        await db.commit()
        user_id = cursor.lastrowid

    # Создаем сессию
    request.session["user_id"] = user_id
    request.session["user_role"] = role

    return RedirectResponse(url="/profile", status_code=302)


@router.get("/logout")
async def logout(request: Request):
    """Выход из системы"""
    request.session.clear()
    return RedirectResponse(url="/", status_code=302)


@router.post("/api/auth/login")
async def api_login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: aiosqlite.Connection = Depends(get_db),
):
    """API вход для получения JWT токена"""
    async with db.execute(
        "SELECT * FROM users WHERE email = ?", (form_data.username,)
    ) as cursor:
        user_row = await cursor.fetchone()

    if user_row is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Неверный email или пароль",
        )

    user = dict(user_row)

    if not verify_password(form_data.password, user["hashed_password"]):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Неверный email или пароль",
        )

    if not user["is_active"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Аккаунт заблокирован",
        )

    access_token = create_access_token(
        data={"sub": str(user["id"]), "role": user["role"]}
    )

    return {
        "access_token": access_token,
        "token_type": "bearer",
        "user_id": user["id"],
        "role": user["role"],
    }


@router.post("/api/auth/register")
async def api_register(
    email: str,
    password: str,
    username: str,
    phone: Optional[str] = None,
    db: aiosqlite.Connection = Depends(get_db),
):
    """API регистрация"""
    # Проверяем минимальную длину пароля
    if len(password) < 6:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Пароль должен содержать минимум 6 символов",
        )

    # Проверяем уникальность email
    async with db.execute("SELECT id FROM users WHERE email = ?", (email,)) as cursor:
        if await cursor.fetchone():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Пользователь с таким email уже существует",
            )

    # Проверяем уникальность username
    async with db.execute("SELECT id FROM users WHERE username = ?", (username,)) as cursor:
        if await cursor.fetchone():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Пользователь с таким именем уже существует",
            )

    # Проверяем уникальность телефона (если указан)
    if phone:
        async with db.execute("SELECT id FROM users WHERE phone = ?", (phone,)) as cursor:
            if await cursor.fetchone():
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Пользователь с таким телефоном уже существует",
                )

    # Хешируем пароль
    hashed_password = get_password_hash(password)

    # Определяем роль (первый пользователь - админ)
    async with db.execute("SELECT COUNT(*) as count FROM users") as cursor:
        count_row = await cursor.fetchone()
        role = UserRole.ADMIN.value if count_row["count"] == 0 else UserRole.USER.value

    # Создаем пользователя
    async with db.execute(
        """
        INSERT INTO users (email, phone, username, hashed_password, role, is_active, created_at, updated_at)
        VALUES (?, ?, ?, ?, ?, 1, ?, ?)
        """,
        (email, phone or None, username, hashed_password, role, datetime.utcnow(), datetime.utcnow()),
    ) as cursor:
        await db.commit()
        user_id = cursor.lastrowid

    # Создаем JWT токен
    access_token = create_access_token(data={"sub": str(user_id), "role": role})

    return {
        "access_token": access_token,
        "token_type": "bearer",
        "user_id": user_id,
        "role": role,
    }


@router.get("/api/auth/me")
async def api_me(
    request: Request,
    db: aiosqlite.Connection = Depends(get_db),
):
    """Получение информации о текущем пользователе"""
    user_id = request.session.get("user_id")
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Не авторизован",
        )

    async with db.execute("SELECT * FROM users WHERE id = ?", (user_id,)) as cursor:
        user_row = await cursor.fetchone()

    if user_row is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Пользователь не найден",
        )

    user = dict(user_row)
    user.pop("hashed_password", None)

    return user
