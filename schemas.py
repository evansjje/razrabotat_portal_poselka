# schemas.py
from pydantic import BaseModel, EmailStr, Field
from typing import Optional
from datetime import datetime
from models import UserRole, PostCategory


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class RegisterRequest(BaseModel):
    email: EmailStr
    phone: Optional[str] = None
    username: str = Field(..., min_length=3, max_length=50)
    password: str = Field(..., min_length=6)


class UserResponse(BaseModel):
    id: int
    email: EmailStr
    phone: Optional[str] = None
    username: str
    role: UserRole
    is_active: bool
    created_at: datetime

    class Config:
        from_attributes = True


class PostResponse(BaseModel):
    id: int
    title: str
    content: str
    category: PostCategory
    author_id: int
    is_published: bool
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class ThemeResponse(BaseModel):
    id: int
    name: str
    primary_color: str
    secondary_color: str
    header_bg: str
    header_text: str
    button_bg: str
    button_text: str
    banner_url: str
    footer_bg: str
    footer_text: str

    class Config:
        from_attributes = True


class ThemeUpdateRequest(BaseModel):
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


class SettingsUpdateRequest(BaseModel):
    key: str
    value: str


class MessageResponse(BaseModel):
    message: str
    success: bool = True
