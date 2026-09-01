from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Optional


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file='.env', extra='ignore')

    # Основные настройки
    APP_NAME: str = "Портал поселка Талакан"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = True
    SECRET_KEY: str = "your-secret-key-change-in-production"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24

    # База данных
    DATABASE_URL: str = "sqlite:///./talakan.db"

    # Почта
    SMTP_HOST: Optional[str] = None
    SMTP_PORT: Optional[int] = None
    SMTP_USER: Optional[str] = None
    SMTP_PASSWORD: Optional[str] = None

    # Погода (OpenWeatherMap)
    WEATHER_API_KEY: Optional[str] = None
    WEATHER_CITY: str = "Talakakan"
    WEATHER_LAT: float = 49.7333
    WEATHER_LON: float = 129.6833

    # Админ
    ADMIN_EMAIL: str = "admin@talakan.ru"
    ADMIN_PASSWORD: str = "admin123"

    # Тема по умолчанию
    DEFAULT_THEME: dict = {
        "primary_color": "#3B82F6",
        "secondary_color": "#10B981",
        "header_bg": "#1F2937",
        "header_text": "#FFFFFF",
        "button_bg": "#3B82F6",
        "button_text": "#FFFFFF",
        "banner_url": "/static/img/banner.jpg",
        "footer_bg": "#1F2937",
        "footer_text": "#FFFFFF"
    }

    # Пути
    STATIC_DIR: str = "static"
    TEMPLATES_DIR: str = "templates"
    UPLOAD_DIR: str = "static/uploads"

    # Лимиты
    MAX_UPLOAD_SIZE: int = 5 * 1024 * 1024  # 5MB
    ALLOWED_EXTENSIONS: set = {"jpg", "jpeg", "png", "gif", "webp"}


settings = Settings()
