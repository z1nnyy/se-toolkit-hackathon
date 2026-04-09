from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel.ext.asyncio.session import AsyncSession

from cava_backend.auth import (
    generate_session_token,
    get_current_auth_context,
    hash_password,
    hash_session_token,
    require_authenticated_user,
    require_super_admin,
    verify_password,
)
from cava_backend.database import get_session
from cava_backend.db.users import (
    count_active_super_admins,
    create_session,
    create_user,
    delete_session_by_token_hash,
    read_all_users,
    read_user_by_username,
    update_user,
)
from cava_backend.models.user import (
    AppUserRecord,
    AuthLoginRequest,
    AuthLoginResponse,
    AuthenticatedUser,
    UserCreateRequest,
    UserUpdateRequest,
    utc_now,
)


router = APIRouter()


def to_public_user(user: AppUserRecord) -> AuthenticatedUser:
    return AuthenticatedUser(
        id=user.id or 0,
        username=user.username,
        full_name=user.full_name,
        role=user.role,
        is_active=user.is_active,
        created_at=user.created_at,
        last_login_at=user.last_login_at,
    )


@router.post("/login", response_model=AuthLoginResponse)
async def login(
    payload: AuthLoginRequest,
    session: AsyncSession = Depends(get_session),
) -> AuthLoginResponse:
    user = await read_user_by_username(session, payload.username)
    if user is None or not verify_password(
        payload.password,
        salt_b64=user.password_salt,
        expected_hash=user.password_hash,
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid username or password",
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="This account has been disabled",
        )

    session_token = generate_session_token()
    await create_session(
        session,
        user_id=user.id or 0,
        token_hash=hash_session_token(session_token),
    )

    user.last_login_at = utc_now()
    await update_user(session, user)

    return AuthLoginResponse(
        access_token=session_token,
        user=to_public_user(user),
    )


@router.get("/me", response_model=AuthenticatedUser)
async def get_me(
    user: AppUserRecord = Depends(require_authenticated_user),
) -> AuthenticatedUser:
    return to_public_user(user)


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout(
    context: tuple[AppUserRecord, object, str] = Depends(get_current_auth_context),
    session: AsyncSession = Depends(get_session),
) -> None:
    await delete_session_by_token_hash(session, context[2])


@router.get("/users", response_model=list[AuthenticatedUser])
async def get_users(
    _: AppUserRecord = Depends(require_super_admin),
    session: AsyncSession = Depends(get_session),
) -> list[AuthenticatedUser]:
    users = await read_all_users(session)
    return [to_public_user(user) for user in users]


@router.post(
    "/users",
    response_model=AuthenticatedUser,
    status_code=status.HTTP_201_CREATED,
)
async def post_user(
    payload: UserCreateRequest,
    _: AppUserRecord = Depends(require_super_admin),
    session: AsyncSession = Depends(get_session),
) -> AuthenticatedUser:
    existing_user = await read_user_by_username(session, payload.username)
    if existing_user is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A user with this username already exists",
        )

    salt, password_hash = hash_password(payload.password)
    user = AppUserRecord(
        username=payload.username,
        full_name=payload.full_name,
        role=payload.role,
        password_salt=salt,
        password_hash=password_hash,
        is_active=payload.is_active,
    )
    created_user = await create_user(session, user)
    return to_public_user(created_user)


@router.patch("/users/{user_id}", response_model=AuthenticatedUser)
async def patch_user(
    user_id: int,
    payload: UserUpdateRequest,
    _: AppUserRecord = Depends(require_super_admin),
    session: AsyncSession = Depends(get_session),
) -> AuthenticatedUser:
    user = await session.get(AppUserRecord, user_id)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    next_role = payload.role if payload.role is not None else user.role
    next_active = payload.is_active if payload.is_active is not None else user.is_active

    if user.role == "super_admin" and (next_role != "super_admin" or not next_active):
        active_super_admins = await count_active_super_admins(session)
        if active_super_admins <= 1:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="You cannot remove access from the last active super admin",
            )

    if payload.full_name is not None:
        user.full_name = payload.full_name
    if payload.role is not None:
        user.role = payload.role
    if payload.is_active is not None:
        user.is_active = payload.is_active
    if payload.password is not None:
        salt, password_hash = hash_password(payload.password)
        user.password_salt = salt
        user.password_hash = password_hash

    updated_user = await update_user(session, user)
    return to_public_user(updated_user)
