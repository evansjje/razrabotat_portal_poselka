# main.py
from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse
from contextlib import asynccontextmanager
import aiosqlite
from config import settings
from database import init_db, DB_PATH
from dependencies import templates, get_theme_settings
from routers import api_router

@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("INSERT OR IGNORE INTO users (email, username, hashed_password, role) VALUES (?, ?, ?, ?)",
                         (settings.ADMIN_EMAIL, "admin", "$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewdBPj4JQyVBqQ2m", "admin"))
        await db.commit()
    yield

app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    debug=settings.DEBUG,
    lifespan=lifespan
)

app.mount("/static", StaticFiles(directory=settings.STATIC_DIR), name="static")
app.include_router(api_router)

@app.get("/", response_class=HTMLResponse)
async def root(request: Request):
    from dependencies import get_db
    db = await get_db().__anext__()
    theme = await get_theme_settings(db)
    await db.close()
    return templates.TemplateResponse(request, "index.html", {
        "request": request,
        "theme": theme,
        "current_page": "main",
        "user": None,
        "news": [],
        "board_posts": []
    })

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
