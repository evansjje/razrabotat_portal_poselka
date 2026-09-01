# services/theme_service.py
import aiosqlite
from typing import Dict, Any, Optional, List
from config import settings
from database import DB_PATH


async def get_theme_settings(db: Optional[aiosqlite.Connection] = None) -> Dict[str, str]:
    """Get current active theme settings"""
    if db is None:
        db = await aiosqlite.connect(DB_PATH)
        db.row_factory = aiosqlite.Row
        should_close = True
    else:
        should_close = False

    try:
        async with db.execute(
            "SELECT * FROM themes ORDER BY id DESC LIMIT 1"
        ) as cursor:
            theme = await cursor.fetchone()

        if theme is None:
            return settings.DEFAULT_THEME

        return {
            "primary_color": theme["primary_color"],
            "secondary_color": theme["secondary_color"],
            "header_bg": theme["header_bg"],
            "header_text": theme["header_text"],
            "button_bg": theme["button_bg"],
            "button_text": theme["button_text"],
            "banner_url": theme["banner_url"],
            "footer_bg": theme["footer_bg"],
            "footer_text": theme["footer_text"],
        }
    finally:
        if should_close:
            await db.close()


async def update_theme_settings(
    theme_data: Dict[str, str],
    db: Optional[aiosqlite.Connection] = None,
) -> Dict[str, str]:
    """Update current theme settings"""
    if db is None:
        db = await aiosqlite.connect(DB_PATH)
        db.row_factory = aiosqlite.Row
        should_close = True
    else:
        should_close = False

    try:
        # Check if any theme exists
        async with db.execute("SELECT id FROM themes ORDER BY id DESC LIMIT 1") as cursor:
            existing = await cursor.fetchone()

        if existing:
            # Update existing theme
            set_clause = ", ".join([f"{key} = ?" for key in theme_data.keys()])
            values = list(theme_data.values())
            values.append(existing["id"])
            await db.execute(
                f"UPDATE themes SET {set_clause} WHERE id = ?",
                values,
            )
        else:
            # Create new theme
            columns = ", ".join(theme_data.keys())
            placeholders = ", ".join(["?"] * len(theme_data))
            values = list(theme_data.values())
            await db.execute(
                f"INSERT INTO themes ({columns}) VALUES ({placeholders})",
                values,
            )

        await db.commit()
        return theme_data
    finally:
        if should_close:
            await db.close()


async def get_all_themes(db: Optional[aiosqlite.Connection] = None) -> List[Dict[str, Any]]:
    """Get all themes"""
    if db is None:
        db = await aiosqlite.connect(DB_PATH)
        db.row_factory = aiosqlite.Row
        should_close = True
    else:
        should_close = False

    try:
        async with db.execute("SELECT * FROM themes ORDER BY id DESC") as cursor:
            themes = await cursor.fetchall()
        return [dict(theme) for theme in themes]
    finally:
        if should_close:
            await db.close()


async def create_theme(
    theme_data: Dict[str, str],
    db: Optional[aiosqlite.Connection] = None,
) -> Dict[str, Any]:
    """Create a new theme"""
    if db is None:
        db = await aiosqlite.connect(DB_PATH)
        db.row_factory = aiosqlite.Row
        should_close = True
    else:
        should_close = False

    try:
        columns = ", ".join(theme_data.keys())
        placeholders = ", ".join(["?"] * len(theme_data))
        values = list(theme_data.values())

        await db.execute(
            f"INSERT INTO themes ({columns}) VALUES ({placeholders})",
            values,
        )
        await db.commit()

        async with db.execute("SELECT * FROM themes WHERE name = ?", (theme_data["name"],)) as cursor:
            theme = await cursor.fetchone()
        return dict(theme) if theme else None
    finally:
        if should_close:
            await db.close()


async def delete_theme(
    theme_id: int,
    db: Optional[aiosqlite.Connection] = None,
) -> bool:
    """Delete a theme by ID"""
    if db is None:
        db = await aiosqlite.connect(DB_PATH)
        db.row_factory = aiosqlite.Row
        should_close = True
    else:
        should_close = False

    try:
        async with db.execute("DELETE FROM themes WHERE id = ?", (theme_id,)) as cursor:
            deleted = cursor.rowcount > 0
        await db.commit()
        return deleted
    finally:
        if should_close:
            await db.close()


async def apply_theme(
    theme_id: int,
    db: Optional[aiosqlite.Connection] = None,
) -> Dict[str, str]:
    """Apply a theme by making it the most recent (active)"""
    if db is None:
        db = await aiosqlite.connect(DB_PATH)
        db.row_factory = aiosqlite.Row
        should_close = True
    else:
        should_close = False

    try:
        # Get the theme to apply
        async with db.execute("SELECT * FROM themes WHERE id = ?", (theme_id,)) as cursor:
            theme = await cursor.fetchone()

        if theme is None:
            return settings.DEFAULT_THEME

        # Update the theme's timestamp to make it most recent
        await db.execute(
            "UPDATE themes SET id = id WHERE id = ?",
            (theme_id,),
        )
        await db.commit()

        return {
            "primary_color": theme["primary_color"],
            "secondary_color": theme["secondary_color"],
            "header_bg": theme["header_bg"],
            "header_text": theme["header_text"],
            "button_bg": theme["button_bg"],
            "button_text": theme["button_text"],
            "banner_url": theme["banner_url"],
            "footer_bg": theme["footer_bg"],
            "footer_text": theme["footer_text"],
        }
    finally:
        if should_close:
            await db.close()
