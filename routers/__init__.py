# routers/__init__.py
from fastapi import APIRouter
from routers.main_page import router as main_page_router
from routers.news import router as news_router
from routers.board import router as board_router
from routers.weather import router as weather_router
from routers.auth import router as auth_router
from routers.profile import router as profile_router
from routers.admin import router as admin_router

api_router = APIRouter()
api_router.include_router(main_page_router, tags=["main"])
api_router.include_router(news_router, prefix="/news", tags=["news"])
api_router.include_router(board_router, prefix="/board", tags=["board"])
api_router.include_router(weather_router, prefix="/weather", tags=["weather"])
api_router.include_router(auth_router, prefix="/auth", tags=["auth"])
api_router.include_router(profile_router, prefix="/profile", tags=["profile"])
api_router.include_router(admin_router, prefix="/admin", tags=["admin"])

__all__ = ["api_router"]
