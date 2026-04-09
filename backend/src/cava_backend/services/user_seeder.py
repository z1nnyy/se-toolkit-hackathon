from __future__ import annotations

from sqlmodel.ext.asyncio.session import AsyncSession

from cava_backend.auth import hash_password
from cava_backend.database import engine
from cava_backend.db.users import create_user, read_user_by_username
from cava_backend.models.user import AppUserRecord
from cava_backend.settings import settings


async def ensure_default_super_admin() -> None:
    async with AsyncSession(engine) as session:
        existing_user = await read_user_by_username(session, settings.superadmin_username)
        if existing_user is not None:
            return

        salt, password_hash = hash_password(settings.superadmin_password)
        super_admin = AppUserRecord(
            username=settings.superadmin_username,
            full_name=settings.superadmin_full_name,
            role="super_admin",
            password_salt=salt,
            password_hash=password_hash,
            is_active=True,
        )
        await create_user(session, super_admin)
