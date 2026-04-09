from __future__ import annotations

from datetime import timedelta

from sqlmodel import delete, func, select
from sqlmodel.ext.asyncio.session import AsyncSession

from cava_backend.models.user import AppUserRecord, UserSessionRecord, utc_now
from cava_backend.settings import settings


async def read_user_by_username(
    session: AsyncSession,
    username: str,
) -> AppUserRecord | None:
    statement = select(AppUserRecord).where(AppUserRecord.username == username)
    result = await session.exec(statement)
    return result.first()


async def read_user_by_id(session: AsyncSession, user_id: int) -> AppUserRecord | None:
    return await session.get(AppUserRecord, user_id)


async def read_all_users(session: AsyncSession) -> list[AppUserRecord]:
    statement = select(AppUserRecord).order_by(AppUserRecord.role, AppUserRecord.username)
    result = await session.exec(statement)
    return list(result.all())


async def create_user(session: AsyncSession, user: AppUserRecord) -> AppUserRecord:
    session.add(user)
    await session.commit()
    await session.refresh(user)
    return user


async def update_user(session: AsyncSession, user: AppUserRecord) -> AppUserRecord:
    session.add(user)
    await session.commit()
    await session.refresh(user)
    return user


async def count_active_super_admins(session: AsyncSession) -> int:
    statement = select(func.count()).select_from(AppUserRecord).where(
        AppUserRecord.role == "super_admin",
        AppUserRecord.is_active.is_(True),
    )
    result = await session.exec(statement)
    return int(result.one())


async def create_session(
    session: AsyncSession,
    *,
    user_id: int,
    token_hash: str,
) -> UserSessionRecord:
    expires_at = utc_now() + timedelta(hours=settings.auth_session_hours)
    user_session = UserSessionRecord(
        user_id=user_id,
        token_hash=token_hash,
        expires_at=expires_at,
    )
    session.add(user_session)
    await session.commit()
    await session.refresh(user_session)
    return user_session


async def read_session_by_token_hash(
    session: AsyncSession,
    token_hash: str,
) -> UserSessionRecord | None:
    statement = select(UserSessionRecord).where(UserSessionRecord.token_hash == token_hash)
    result = await session.exec(statement)
    return result.first()


async def delete_session_by_token_hash(
    session: AsyncSession,
    token_hash: str,
) -> None:
    await session.exec(delete(UserSessionRecord).where(UserSessionRecord.token_hash == token_hash))
    await session.commit()


async def delete_expired_sessions(session: AsyncSession) -> None:
    await session.exec(
        delete(UserSessionRecord).where(UserSessionRecord.expires_at < utc_now())
    )
    await session.commit()
