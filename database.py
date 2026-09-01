# database.py
import aiosqlite
from contextlib import asynccontextmanager
from typing import AsyncGenerator, Optional
from config import settings

DB_PATH = settings.DATABASE_URL.replace("sqlite:///", "")

async def init_db() -> None:
    """Initialize database tables"""
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        
        # Users table
        await db.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                email TEXT UNIQUE NOT NULL,
                phone TEXT UNIQUE,
                username TEXT UNIQUE NOT NULL,
                hashed_password TEXT NOT NULL,
                role TEXT NOT NULL DEFAULT 'user',
                is_active BOOLEAN NOT NULL DEFAULT 1,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Posts table (news, board)
        await db.execute('''
            CREATE TABLE IF NOT EXISTS posts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                content TEXT NOT NULL,
                category TEXT NOT NULL,
                author_id INTEGER NOT NULL,
                is_published BOOLEAN NOT NULL DEFAULT 1,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (author_id) REFERENCES users (id) ON DELETE CASCADE
            )
        ''')
        
        # Settings table
        await db.execute('''
            CREATE TABLE IF NOT EXISTS settings (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL
            )
        ''')
        
        # Theme settings table
        await db.execute('''
            CREATE TABLE IF NOT EXISTS themes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT UNIQUE NOT NULL,
                primary_color TEXT NOT NULL DEFAULT '#3B82F6',
                secondary_color TEXT NOT NULL DEFAULT '#10B981',
                header_bg TEXT NOT NULL DEFAULT '#1F2937',
                header_text TEXT NOT NULL DEFAULT '#FFFFFF',
                button_bg TEXT NOT NULL DEFAULT '#3B82F6',
                button_text TEXT NOT NULL DEFAULT '#FFFFFF',
                banner_url TEXT NOT NULL DEFAULT '/static/img/banner.jpg',
                footer_bg TEXT NOT NULL DEFAULT '#1F2937',
                footer_text TEXT NOT NULL DEFAULT '#FFFFFF',
                is_active BOOLEAN NOT NULL DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Insert default theme if not exists
        await db.execute('''
            INSERT OR IGNORE INTO themes (name, is_active)
            VALUES ('default', 1)
        ''')
        
        # Insert default settings
        await db.execute('''
            INSERT OR IGNORE INTO settings (key, value)
            VALUES ('site_name', ?), ('site_description', ?)
        ''', (settings.APP_NAME, 'Портал поселка Талакан'))
        
        await db.commit()

@asynccontextmanager
async def get_db() -> AsyncGenerator[aiosqlite.Connection, None]:
    """Database dependency"""
    db = await aiosqlite.connect(DB_PATH)
    db.row_factory = aiosqlite.Row
    try:
        yield db
        await db.commit()
    except Exception:
        await db.rollback()
        raise
    finally:
        await db.close()

async def get_user_by_email(db: aiosqlite.Connection, email: str) -> Optional[aiosqlite.Row]:
    """Get user by email"""
    cursor = await db.execute('SELECT * FROM users WHERE email = ?', (email,))
    return await cursor.fetchone()

async def get_user_by_username(db: aiosqlite.Connection, username: str) -> Optional[aiosqlite.Row]:
    """Get user by username"""
    cursor = await db.execute('SELECT * FROM users WHERE username = ?', (username,))
    return await cursor.fetchone()

async def get_user_by_id(db: aiosqlite.Connection, user_id: int) -> Optional[aiosqlite.Row]:
    """Get user by ID"""
    cursor = await db.execute('SELECT * FROM users WHERE id = ?', (user_id,))
    return await cursor.fetchone()

async def create_user(db: aiosqlite.Connection, email: str, phone: str, username: str, hashed_password: str, role: str = 'user') -> int:
    """Create new user"""
    cursor = await db.execute(
        'INSERT INTO users (email, phone, username, hashed_password, role) VALUES (?, ?, ?, ?, ?)',
        (email, phone, username, hashed_password, role)
    )
    await db.commit()
    return cursor.lastrowid

async def update_user(db: aiosqlite.Connection, user_id: int, **kwargs) -> None:
    """Update user fields"""
    if not kwargs:
        return
    fields = ', '.join(f'{k} = ?' for k in kwargs.keys())
    values = list(kwargs.values()) + [user_id]
    await db.execute(f'UPDATE users SET {fields}, updated_at = CURRENT_TIMESTAMP WHERE id = ?', values)
    await db.commit()

async def delete_user(db: aiosqlite.Connection, user_id: int) -> None:
    """Delete user"""
    await db.execute('DELETE FROM users WHERE id = ?', (user_id,))
    await db.commit()

async def get_all_users(db: aiosqlite.Connection) -> list[aiosqlite.Row]:
    """Get all users"""
    cursor = await db.execute('SELECT * FROM users ORDER BY created_at DESC')
    return await cursor.fetchall()

async def create_post(db: aiosqlite.Connection, title: str, content: str, category: str, author_id: int, is_published: bool = True) -> int:
    """Create new post"""
    cursor = await db.execute(
        'INSERT INTO posts (title, content, category, author_id, is_published) VALUES (?, ?, ?, ?, ?)',
        (title, content, category, author_id, is_published)
    )
    await db.commit()
    return cursor.lastrowid

async def get_post_by_id(db: aiosqlite.Connection, post_id: int) -> Optional[aiosqlite.Row]:
    """Get post by ID"""
    cursor = await db.execute('SELECT * FROM posts WHERE id = ?', (post_id,))
    return await cursor.fetchone()

async def get_posts_by_category(db: aiosqlite.Connection, category: str, limit: int = 10, offset: int = 0) -> list[aiosqlite.Row]:
    """Get posts by category"""
    cursor = await db.execute(
        'SELECT * FROM posts WHERE category = ? AND is_published = 1 ORDER BY created_at DESC LIMIT ? OFFSET ?',
        (category, limit, offset)
    )
    return await cursor.fetchall()

async def get_all_posts(db: aiosqlite.Connection, limit: int = 10, offset: int = 0) -> list[aiosqlite.Row]:
    """Get all published posts"""
    cursor = await db.execute(
        'SELECT * FROM posts WHERE is_published = 1 ORDER BY created_at DESC LIMIT ? OFFSET ?',
        (limit, offset)
    )
    return await cursor.fetchall()

async def update_post(db: aiosqlite.Connection, post_id: int, **kwargs) -> None:
    """Update post fields"""
    if not kwargs:
        return
    fields = ', '.join(f'{k} = ?' for k in kwargs.keys())
    values = list(kwargs.values()) + [post_id]
    await db.execute(f'UPDATE posts SET {fields}, updated_at = CURRENT_TIMESTAMP WHERE id = ?', values)
    await db.commit()

async def delete_post(db: aiosqlite.Connection, post_id: int) -> None:
    """Delete post"""
    await db.execute('DELETE FROM posts WHERE id = ?', (post_id,))
    await db.commit()

async def get_setting(db: aiosqlite.Connection, key: str) -> Optional[str]:
    """Get setting value"""
    cursor = await db.execute('SELECT value FROM settings WHERE key = ?', (key,))
    row = await cursor.fetchone()
    return row['value'] if row else None

async def set_setting(db: aiosqlite.Connection, key: str, value: str) -> None:
    """Set setting value"""
    await db.execute(
        'INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)',
        (key, value)
    )
    await db.commit()

async def get_active_theme(db: aiosqlite.Connection) -> Optional[aiosqlite.Row]:
    """Get active theme"""
    cursor = await db.execute('SELECT * FROM themes WHERE is_active = 1 LIMIT 1')
    return await cursor.fetchone()

async def get_all_themes(db: aiosqlite.Connection) -> list[aiosqlite.Row]:
    """Get all themes"""
    cursor = await db.execute('SELECT * FROM themes ORDER BY created_at DESC')
    return await cursor.fetchall()

async def create_theme(db: aiosqlite.Connection, name: str, **kwargs) -> int:
    """Create new theme"""
    fields = ['name'] + list(kwargs.keys())
    values = [name] + list(kwargs.values())
    placeholders = ', '.join(['?'] * len(fields))
    cursor = await db.execute(
        f'INSERT INTO themes ({", ".join(fields)}) VALUES ({placeholders})',
        values
    )
    await db.commit()
    return cursor.lastrowid

async def update_theme(db: aiosqlite.Connection, theme_id: int, **kwargs) -> None:
    """Update theme fields"""
    if not kwargs:
        return
    fields = ', '.join(f'{k} = ?' for k in kwargs.keys())
    values = list(kwargs.values()) + [theme_id]
    await db.execute(f'UPDATE themes SET {fields} WHERE id = ?', values)
    await db.commit()

async def activate_theme(db: aiosqlite.Connection, theme_id: int) -> None:
    """Activate theme"""
    await db.execute('UPDATE themes SET is_active = 0')
    await db.execute('UPDATE themes SET is_active = 1 WHERE id = ?', (theme_id,))
    await db.commit()

async def delete_theme(db: aiosqlite.Connection, theme_id: int) -> None:
    """Delete theme"""
    await db.execute('DELETE FROM themes WHERE id = ?', (theme_id,))
    await db.commit()

async def get_theme_by_id(db: aiosqlite.Connection, theme_id: int) -> Optional[aiosqlite.Row]:
    """Get theme by ID"""
    cursor = await db.execute('SELECT * FROM themes WHERE id = ?', (theme_id,))
    return await cursor.fetchone()
