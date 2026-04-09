from __future__ import annotations

from datetime import datetime, timezone
from typing import Literal

from sqlmodel import Field, SQLModel


UserRole = Literal["super_admin", "staff_admin"]


def utc_now() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


class AppUserRecord(SQLModel, table=True):
    __tablename__ = "app_user"

    id: int | None = Field(default=None, primary_key=True)
    username: str = Field(index=True, unique=True, min_length=3, max_length=64)
    full_name: str = Field(default="", max_length=120)
    role: str = Field(default="staff_admin", max_length=32)
    password_salt: str = Field(max_length=128)
    password_hash: str = Field(max_length=256)
    is_active: bool = True
    created_at: datetime = Field(default_factory=utc_now)
    last_login_at: datetime | None = None


class UserSessionRecord(SQLModel, table=True):
    __tablename__ = "user_session"

    id: int | None = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="app_user.id", index=True)
    token_hash: str = Field(index=True, unique=True, max_length=128)
    expires_at: datetime = Field(index=True)
    created_at: datetime = Field(default_factory=utc_now)


class AuthLoginRequest(SQLModel):
    username: str
    password: str


class AuthenticatedUser(SQLModel):
    id: int
    username: str
    full_name: str
    role: str
    is_active: bool
    created_at: datetime
    last_login_at: datetime | None = None


class AuthLoginResponse(SQLModel):
    access_token: str
    user: AuthenticatedUser


class UserCreateRequest(SQLModel):
    username: str = Field(min_length=3, max_length=64)
    full_name: str = Field(default="", max_length=120)
    role: UserRole = "staff_admin"
    password: str = Field(min_length=8, max_length=128)
    is_active: bool = True


class UserUpdateRequest(SQLModel):
    full_name: str | None = Field(default=None, max_length=120)
    role: UserRole | None = None
    password: str | None = Field(default=None, min_length=8, max_length=128)
    is_active: bool | None = None
