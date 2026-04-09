from __future__ import annotations

import base64
import hashlib
import secrets
from typing import Annotated

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlmodel.ext.asyncio.session import AsyncSession

from cava_backend.database import get_session
from cava_backend.db.users import (
    delete_expired_sessions,
    read_session_by_token_hash,
    read_user_by_id,
)
from cava_backend.models.user import AppUserRecord, UserSessionRecord, utc_now


security = HTTPBearer(auto_error=False)


def hash_password(password: str, *, salt_b64: str | None = None) -> tuple[str, str]:
    salt = (
        base64.b64decode(salt_b64.encode("utf-8"))
        if salt_b64 is not None
        else secrets.token_bytes(16)
    )
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, 200_000)
    return (
        base64.b64encode(salt).decode("utf-8"),
        base64.b64encode(digest).decode("utf-8"),
    )


def verify_password(password: str, *, salt_b64: str, expected_hash: str) -> bool:
    _, calculated_hash = hash_password(password, salt_b64=salt_b64)
    return secrets.compare_digest(calculated_hash, expected_hash)


def generate_session_token() -> str:
    return secrets.token_urlsafe(32)


def hash_session_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


async def get_current_auth_context(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(security)],
    session: Annotated[AsyncSession, Depends(get_session)],
) -> tuple[AppUserRecord, UserSessionRecord, str]:
    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required",
        )

    token = credentials.credentials
    token_hash = hash_session_token(token)

    await delete_expired_sessions(session)
    user_session = await read_session_by_token_hash(session, token_hash)
    if user_session is None or user_session.expires_at < utc_now():
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired session",
        )

    user = await read_user_by_id(session, user_session.user_id)
    if user is None or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User account is inactive",
        )

    return user, user_session, token_hash


async def require_authenticated_user(
    context: Annotated[tuple[AppUserRecord, UserSessionRecord, str], Depends(get_current_auth_context)],
) -> AppUserRecord:
    return context[0]


async def require_menu_admin(
    user: Annotated[AppUserRecord, Depends(require_authenticated_user)],
) -> AppUserRecord:
    if user.role not in {"staff_admin", "super_admin"}:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Menu access is forbidden for this role",
        )
    return user


async def require_super_admin(
    user: Annotated[AppUserRecord, Depends(require_authenticated_user)],
) -> AppUserRecord:
    if user.role != "super_admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only the main administrator can manage users",
        )
    return user
