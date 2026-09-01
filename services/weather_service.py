# services/weather_service.py
import aiosqlite
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta
import json
import urllib.request
import urllib.parse
from config import settings
from database import DB_PATH


async def get_weather_data(db: Optional[aiosqlite.Connection] = None) -> Dict[str, Any]:
    """Get current weather and forecast for Talakan"""
    if db is None:
        db = await aiosqlite.connect(DB_PATH)
        db.row_factory = aiosqlite.Row
        should_close = True
    else:
        should_close = False

    try:
        # Check cache first
        async with db.execute(
            """
            SELECT value, updated_at 
            FROM settings 
            WHERE key = 'weather_cache'
            """
        ) as cursor:
            cached = await cursor.fetchone()

        if cached:
            cache_time = datetime.fromisoformat(cached["updated_at"])
            if datetime.now() - cache_time < timedelta(minutes=30):
                return json.loads(cached["value"])

        # Fetch from OpenWeatherMap
        weather_data = await _fetch_weather_from_api()

        # Cache the result
        if weather_data:
            await db.execute(
                """
                INSERT OR REPLACE INTO settings (key, value, updated_at)
                VALUES ('weather_cache', ?, ?)
                """,
                (
                    json.dumps(weather_data, ensure_ascii=False),
                    datetime.now().isoformat(),
                ),
            )
            await db.commit()

        return weather_data
    finally:
        if should_close:
            await db.close()


async def _fetch_weather_from_api() -> Dict[str, Any]:
    """Fetch weather data from OpenWeatherMap API"""
    if not settings.WEATHER_API_KEY:
        return _get_fallback_weather()

    try:
        # Current weather
        current_url = (
            f"https://api.openweathermap.org/data/2.5/weather"
            f"?lat={settings.WEATHER_LAT}&lon={settings.WEATHER_LON}"
            f"&appid={settings.WEATHER_API_KEY}&units=metric&lang=ru"
        )

        with urllib.request.urlopen(current_url, timeout=10) as response:
            current_data = json.loads(response.read().decode())

        # Forecast
        forecast_url = (
            f"https://api.openweathermap.org/data/2.5/forecast"
            f"?lat={settings.WEATHER_LAT}&lon={settings.WEATHER_LON}"
            f"&appid={settings.WEATHER_API_KEY}&units=metric&lang=ru"
        )

        with urllib.request.urlopen(forecast_url, timeout=10) as response:
            forecast_data = json.loads(response.read().decode())

        # Process current weather
        weather = {
            "temperature": round(current_data["main"]["temp"]),
            "feels_like": round(current_data["main"]["feels_like"]),
            "humidity": current_data["main"]["humidity"],
            "pressure": current_data["main"]["pressure"],
            "wind_speed": round(current_data["wind"]["speed"], 1),
            "wind_direction": _get_wind_direction(current_data["wind"]["deg"]),
            "description": current_data["weather"][0]["description"].capitalize(),
            "icon": current_data["weather"][0]["icon"],
            "city": current_data.get("name", settings.WEATHER_CITY),
            "sunrise": datetime.fromtimestamp(current_data["sys"]["sunrise"]).strftime("%H:%M"),
            "sunset": datetime.fromtimestamp(current_data["sys"]["sunset"]).strftime("%H:%M"),
        }

        # Process forecast
        forecast = []
        seen_dates = set()
        for item in forecast_data.get("list", []):
            date = item["dt_txt"][:10]
            if date not in seen_dates and len(forecast) < 7:
                seen_dates.add(date)
                forecast.append({
                    "date": date,
                    "temperature": round(item["main"]["temp"]),
                    "feels_like": round(item["main"]["feels_like"]),
                    "humidity": item["main"]["humidity"],
                    "wind_speed": round(item["wind"]["speed"], 1),
                    "description": item["weather"][0]["description"].capitalize(),
                    "icon": item["weather"][0]["icon"],
                })

        return {
            "current": weather,
            "forecast": forecast,
            "source": "openweathermap",
            "updated_at": datetime.now().isoformat(),
        }

    except Exception as e:
        print(f"Weather API error: {e}")
        return _get_fallback_weather()


def _get_fallback_weather() -> Dict[str, Any]:
    """Return fallback weather data when API is unavailable"""
    now = datetime.now()
    return {
        "current": {
            "temperature": -5,
            "feels_like": -8,
            "humidity": 75,
            "pressure": 1013,
            "wind_speed": 3.5,
            "wind_direction": "СЗ",
            "description": "Переменная облачность",
            "icon": "04d",
            "city": settings.WEATHER_CITY,
            "sunrise": "07:30",
            "sunset": "17:45",
        },
        "forecast": [
            {
                "date": (now + timedelta(days=i)).strftime("%Y-%m-%d"),
                "temperature": -5 + i,
                "feels_like": -8 + i,
                "humidity": 70 + i,
                "wind_speed": 3.0 + i * 0.5,
                "description": "Облачно",
                "icon": "04d",
            }
            for i in range(7)
        ],
        "source": "fallback",
        "updated_at": now.isoformat(),
    }


def _get_wind_direction(degrees: float) -> str:
    """Convert wind degrees to direction name"""
    directions = ["С", "СВ", "В", "ЮВ", "Ю", "ЮЗ", "З", "СЗ"]
    index = round(degrees / 45) % 8
    return directions[index]
