import uuid
from datetime import datetime
from enum import Enum

from pydantic import BaseModel, EmailStr, Field, field_validator


# ─── User Schemas ─────────────────────────────────────────────────────────────

class UserRole(str, Enum):
    ADMIN = "admin"
    BARBER = "barber"
    RECEPTIONIST = "receptionist"


class UserBase(BaseModel):
    name: str = Field(..., min_length=2, max_length=150)
    email: EmailStr
    phone: str | None = None
    role: UserRole = UserRole.BARBER


class UserCreate(UserBase):
    password: str = Field(..., min_length=8)


class UserUpdate(BaseModel):
    name: str | None = None
    phone: str | None = None
    avatar_url: str | None = None
    is_active: bool | None = None


class UserOut(UserBase):
    id: uuid.UUID
    is_active: bool
    avatar_url: str | None
    created_at: datetime

    model_config = {"from_attributes": True}


# ─── Auth Schemas ─────────────────────────────────────────────────────────────

class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    user: UserOut


class RefreshRequest(BaseModel):
    refresh_token: str
