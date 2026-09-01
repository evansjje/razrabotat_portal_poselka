# routers/weather.py
from fastapi import APIRouter, Request, Depends
from fastapi.responses import HTMLResponse
from typing import Dict, Any
import aiosqlite
from dependencies import templates, get_db, get_theme_settings
from services.weather_service import get_weather_data

router = APIRouter()


@router.get("/", response_class=HTMLResponse)
async def weather_page(
    request: Request,
    db: aiosqlite.Connection = Depends(get_db),
    theme: Dict[str, str] = Depends(get_theme_settings),
):
    """Страница погоды"""
    # Получаем текущего пользователя
    user = None
    if "user_id" in request.session:
        async with db.execute(
            "SELECT * FROM users WHERE id = ?", (request.session["user_id"],)
        ) as cursor:
            user_row = await cursor.fetchone()
            if user_row:
                user = dict(user_row)

    # Получаем данные о погоде
    weather_data = await get_weather_data()

    return templates.TemplateResponse(
        request,
        "weather.html",
        {
            "request": request,
            "user": user,
            "theme": theme,
            "current_page": "weather",
            "weather": weather_data,
        },
    )


@router.get("/api/weather/current")
async def get_current_weather():
    """API endpoint для получения текущей погоды"""
    weather_data = await get_weather_data()
    return weather_data


@router.get("/api/weather/forecast")
async def get_weather_forecast(days: int = 7):
    """API endpoint для получения прогноза погоды"""
    weather_data = await get_weather_data()
    if weather_data and "forecast" in weather_data:
        return {"forecast": weather_data["forecast"][:days]}
    return {"forecast": []}
