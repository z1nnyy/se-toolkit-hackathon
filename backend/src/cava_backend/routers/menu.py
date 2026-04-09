from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import FileResponse, Response
from sqlmodel.ext.asyncio.session import AsyncSession

from cava_backend.auth import require_menu_admin
from cava_backend.database import get_session
from cava_backend.db.menu_items import (
    create_menu_collection,
    create_menu_item,
    delete_menu_collection,
    delete_menu_item,
    read_menu_catalog,
    read_menu_groups,
    read_menu_item,
    read_menu_items,
    read_menu_summary,
    read_sections,
    restore_menu_collection,
    restore_menu_item,
    set_menu_item_availability,
    update_menu_item,
)
from cava_backend.models.menu_item import (
    MenuCollectionCreate,
    MenuCollectionSummary,
    MenuEntryCreate,
    MenuEntryRecord,
    MenuRenderManifest,
    MenuEntryUpdate,
    MenuItemAvailabilityUpdate,
    MenuPoster,
    MenuSummary,
)
from cava_backend.services.menu_render_cache import (
    get_menu_render_cache_path,
    store_menu_render_cache,
)
from cava_backend.services.menu_image_renderer import render_menu_image
from cava_backend.services.menu_image_renderer import build_menu_render_manifest
from cava_backend.models.user import AppUserRecord
from cava_backend.services.posters import get_menu_posters


router = APIRouter()


@router.get("/items", response_model=list[MenuEntryRecord])
async def get_menu_items(
    menu_group: str | None = Query(default=None),
    section: str | None = Query(default=None),
    search: str | None = Query(default=None),
    available_only: bool = Query(default=False),
    unavailable_only: bool = Query(default=False),
    deleted_only: bool = Query(default=False),
    session: AsyncSession = Depends(get_session),
) -> list[MenuEntryRecord]:
    return await read_menu_items(
        session,
        menu_group=menu_group,
        section=section,
        search=search,
        available_only=available_only,
        unavailable_only=unavailable_only,
        deleted_only=deleted_only,
    )


@router.get("/items/{item_id}", response_model=MenuEntryRecord)
async def get_menu_item(
    item_id: int,
    session: AsyncSession = Depends(get_session),
) -> MenuEntryRecord:
    item = await read_menu_item(session, item_id)
    if item is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Menu item not found",
        )
    return item


@router.get("/groups", response_model=list[str])
async def get_groups(
    session: AsyncSession = Depends(get_session),
) -> list[str]:
    return await read_menu_groups(session)


@router.get("/catalog", response_model=list[MenuCollectionSummary])
async def get_menu_catalog(
    session: AsyncSession = Depends(get_session),
) -> list[MenuCollectionSummary]:
    return await read_menu_catalog(session)


@router.get("/sections", response_model=list[str])
async def get_menu_sections(
    menu_group: str | None = Query(default=None),
    session: AsyncSession = Depends(get_session),
) -> list[str]:
    return await read_sections(session, menu_group=menu_group)


@router.get("/posters", response_model=list[MenuPoster])
async def get_posters() -> list[MenuPoster]:
    return get_menu_posters()


@router.get("/summary", response_model=MenuSummary)
async def get_menu_summary(
    session: AsyncSession = Depends(get_session),
) -> MenuSummary:
    return await read_menu_summary(session)


@router.get("/render-manifest", response_model=MenuRenderManifest)
async def get_render_manifest(
    menu_group: str | None = Query(default=None),
    section: str | None = Query(default=None),
    available_only: bool = Query(default=False),
    unavailable_only: bool = Query(default=False),
    language: str = Query(default="ru", pattern="^(ru|en)$"),
    width: int = Query(default=1280, ge=720, le=5000),
    single_page: bool = Query(default=False),
    session: AsyncSession = Depends(get_session),
) -> MenuRenderManifest:
    items = await read_menu_items(
        session,
        menu_group=menu_group,
        section=section,
        available_only=available_only,
        unavailable_only=unavailable_only,
    )
    return build_menu_render_manifest(
        items,
        language=language,
        menu_group=menu_group,
        section=section,
        available_only=available_only,
        unavailable_only=unavailable_only,
        width=width,
        single_page=single_page,
    )


@router.get("/render", response_class=Response)
async def render_menu(
    menu_group: str | None = Query(default=None),
    section: str | None = Query(default=None),
    available_only: bool = Query(default=False),
    unavailable_only: bool = Query(default=False),
    language: str = Query(default="ru", pattern="^(ru|en)$"),
    width: int = Query(default=1280, ge=720, le=5000),
    page: int = Query(default=1, ge=1),
    single_page: bool = Query(default=False),
    session: AsyncSession = Depends(get_session),
) -> Response:
    cached_path = get_menu_render_cache_path(
        language=language,
        menu_group=menu_group,
        section=section,
        available_only=available_only,
        unavailable_only=unavailable_only,
        width=width,
        page=page,
        single_page=single_page,
    )
    if cached_path.exists():
        return FileResponse(
            path=cached_path,
            media_type="image/png",
            filename="cava-menu.png",
            headers={"Cache-Control": "no-store"},
        )

    items = await read_menu_items(
        session,
        menu_group=menu_group,
        section=section,
        available_only=available_only,
        unavailable_only=unavailable_only,
    )
    image_bytes = render_menu_image(
        items,
        language=language,
        menu_group=menu_group,
        section=section,
        available_only=available_only,
        unavailable_only=unavailable_only,
        width=width,
        page=page,
        single_page=single_page,
    )
    cached_path = store_menu_render_cache(
        image_bytes,
        language=language,
        menu_group=menu_group,
        section=section,
        available_only=available_only,
        unavailable_only=unavailable_only,
        width=width,
        page=page,
        single_page=single_page,
    )
    return FileResponse(
        path=cached_path,
        media_type="image/png",
        filename="cava-menu.png",
        headers={"Cache-Control": "no-store"},
    )


@router.post(
    "/items",
    response_model=MenuEntryRecord,
    status_code=status.HTTP_201_CREATED,
)
async def post_menu_item(
    payload: MenuEntryCreate,
    _: Annotated[AppUserRecord, Depends(require_menu_admin)],
    session: AsyncSession = Depends(get_session),
) -> MenuEntryRecord:
    return await create_menu_item(session, payload)


@router.post(
    "/catalog",
    response_model=MenuCollectionSummary,
    status_code=status.HTTP_201_CREATED,
)
async def post_menu_collection(
    payload: MenuCollectionCreate,
    _: Annotated[AppUserRecord, Depends(require_menu_admin)],
    session: AsyncSession = Depends(get_session),
) -> MenuCollectionSummary:
    collection = await create_menu_collection(session, payload)
    if collection is None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Menu with this name already exists",
        )
    return MenuCollectionSummary(
        id=collection.id or 0,
        name=collection.name,
        created_at=collection.created_at,
        updated_at=collection.updated_at,
        deleted_at=collection.deleted_at,
        active_items=0,
        deleted_items=0,
    )


@router.put(
    "/items/{item_id}",
    response_model=MenuEntryRecord,
)
async def put_menu_item(
    item_id: int,
    payload: MenuEntryUpdate,
    _: Annotated[AppUserRecord, Depends(require_menu_admin)],
    session: AsyncSession = Depends(get_session),
) -> MenuEntryRecord:
    item = await update_menu_item(session, item_id, payload)
    if item is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Menu item not found",
        )
    return item


@router.patch(
    "/items/{item_id}/availability",
    response_model=MenuEntryRecord,
)
async def patch_menu_item_availability(
    item_id: int,
    payload: MenuItemAvailabilityUpdate,
    _: Annotated[AppUserRecord, Depends(require_menu_admin)],
    session: AsyncSession = Depends(get_session),
) -> MenuEntryRecord:
    item = await set_menu_item_availability(
        session,
        item_id,
        is_available=payload.is_available,
    )
    if item is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Menu item not found",
        )
    return item


@router.post(
    "/items/{item_id}/restore",
    response_model=MenuEntryRecord,
)
async def restore_deleted_menu_item(
    item_id: int,
    _: Annotated[AppUserRecord, Depends(require_menu_admin)],
    session: AsyncSession = Depends(get_session),
) -> MenuEntryRecord:
    item = await restore_menu_item(session, item_id)
    if item is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Deleted menu item not found",
        )
    return item


@router.delete(
    "/items/{item_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def remove_menu_item(
    item_id: int,
    _: Annotated[AppUserRecord, Depends(require_menu_admin)],
    session: AsyncSession = Depends(get_session),
) -> None:
    was_deleted = await delete_menu_item(session, item_id)
    if not was_deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Menu item not found",
        )


@router.delete(
    "/catalog/{menu_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def remove_menu_collection(
    menu_id: int,
    _: Annotated[AppUserRecord, Depends(require_menu_admin)],
    session: AsyncSession = Depends(get_session),
) -> None:
    was_deleted = await delete_menu_collection(session, menu_id)
    if not was_deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Menu not found",
        )


@router.post(
    "/catalog/{menu_id}/restore",
    response_model=MenuCollectionSummary,
)
async def restore_deleted_menu_collection(
    menu_id: int,
    _: Annotated[AppUserRecord, Depends(require_menu_admin)],
    session: AsyncSession = Depends(get_session),
) -> MenuCollectionSummary:
    collection = await restore_menu_collection(session, menu_id)
    if collection is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Menu not found",
        )

    catalog = await read_menu_catalog(session)
    restored = next((item for item in catalog if item.id == (collection.id or 0)), None)
    if restored is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Menu not found after restore",
        )
    return restored
