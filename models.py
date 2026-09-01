# models.py
from datetime import datetime
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, EmailStr, Field, ConfigDict
from enum import Enum


class UserRole(str, Enum):
    ADMIN = "admin"
    MODERATOR = "moderator"
    USER = "user"


class UserBase(BaseModel):
    email: EmailStr
    phone: Optional[str] = None
    username: str = Field(..., min_length=3, max_length=50)


class UserCreate(UserBase):
    password: str = Field(..., min_length=6)


class UserUpdate(BaseModel):
    email: Optional[EmailStr] = None
    phone: Optional[str] = None
    username: Optional[str] = None
    password: Optional[str] = None
    role: Optional[UserRole] = None
    is_active: Optional[bool] = None


class UserInDB(UserBase):
    id: int
    hashed_password: str
    role: UserRole = UserRole.USER
    is_active: bool = True
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class User(UserBase):
    id: int
    role: UserRole = UserRole.USER
    is_active: bool = True
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class PostCategory(str, Enum):
    NEWS = "news"
    BOARD = "board"


class PostBase(BaseModel):
    title: str = Field(..., min_length=3, max_length=200)
    content: str = Field(..., min_length=10)
    category: PostCategory


class PostCreate(PostBase):
    author_id: int
    is_published: bool = True


class PostUpdate(BaseModel):
    title: Optional[str] = None
    content: Optional[str] = None
    category: Optional[PostCategory] = None
    is_published: Optional[bool] = None


class PostInDB(PostBase):
    id: int
    author_id: int
    is_published: bool = True
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class Post(PostBase):
    id: int
    author_id: int
    is_published: bool = True
    created_at: datetime
    author: Optional[User] = None

    model_config = ConfigDict(from_attributes=True)


class ThemeBase(BaseModel):
    name: str = Field(..., min_length=3, max_length=50)
    primary_color: str = "#3B82F6"
    secondary_color: str = "#10B981"
    header_bg: str = "#1F2937"
    header_text: str = "#FFFFFF"
    button_bg: str = "#3B82F6"
    button_text: str = "#FFFFFF"
    banner_url: str = "/static/img/banner.jpg"
    footer_bg: str = "#1F2937"
    footer_text: str = "#FFFFFF"


class ThemeCreate(ThemeBase):
    pass


class ThemeUpdate(BaseModel):
    name: Optional[str] = None
    primary_color: Optional[str] = None
    secondary_color: Optional[str] = None
    header_bg: Optional[str] = None
    header_text: Optional[str] = None
    button_bg: Optional[str] = None
    button_text: Optional[str] = None
    banner_url: Optional[str] = None
    footer_bg: Optional[str] = None
    footer_text: Optional[str] = None


class ThemeInDB(ThemeBase):
    id: int

    model_config = ConfigDict(from_attributes=True)


class Theme(ThemeBase):
    id: int

    model_config = ConfigDict(from_attributes=True)


class SettingsBase(BaseModel):
    key: str = Field(..., min_length=1, max_length=100)
    value: str


class SettingsCreate(SettingsBase):
    pass


class SettingsUpdate(BaseModel):
    value: str


class SettingsInDB(SettingsBase):
    id: int

    model_config = ConfigDict(from_attributes=True)


class Settings(SettingsBase):
    id: int

    model_config = ConfigDict(from_attributes=True)


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"


class TokenData(BaseModel):
    username: Optional[str] = None
    user_id: Optional[int] = None


class WeatherData(BaseModel):
    temperature: float
    feels_like: float
    humidity: int
    pressure: int
    wind_speed: float
    description: str
    icon: str
    city: str
    timestamp: datetime


class BoardItem(BaseModel):
    id: int
    title: str
    content: str
    price: Optional[float] = None
    category: str
    author_id: int
    created_at: datetime
    author: Optional[User] = None

    model_config = ConfigDict(from_attributes=True)


class NewsItem(BaseModel):
    id: int
    title: str
    content: str
    author_id: int
    created_at: datetime
    author: Optional[User] = None

    model_config = ConfigDict(from_attributes=True)


class DashboardStats(BaseModel):
    total_users: int
    total_posts: int
    total_news: int
    total_board: int
    active_users: int
    recent_posts: List[Post] = []


class PaginatedResponse(BaseModel):
    items: List[Any]
    total: int
    page: int
    page_size: int
    total_pages: int


class MessageResponse(BaseModel):
    message: str
    success: bool = True


class ErrorResponse(BaseModel):
    error: str
    detail: Optional[str] = None
    status_code: int = 400
