from __future__ import annotations

from sqlalchemy import case, func, or_
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from cava_backend.models.menu_item import (
    MenuCollectionCreate,
    MenuCollectionRecord,
    MenuCollectionSummary,
    MenuEntryCreate,
    MenuEntryRecord,
    MenuEntryUpdate,
    MenuSummary,
    utc_now,
)
from cava_backend.services.menu_localization import ensure_secondary_language_fields
from cava_backend.services.menu_render_cache import invalidate_menu_render_cache


async def ensure_menu_collection(
    session: AsyncSession,
    name: str,
    *,
    restore_if_deleted: bool = False,
) -> MenuCollectionRecord:
    normalized_name = name.strip()
    statement = select(MenuCollectionRecord).where(MenuCollectionRecord.name == normalized_name)
    collection = (await session.exec(statement)).first()
    if collection is None:
        collection = MenuCollectionRecord(name=normalized_name)
        session.add(collection)
        await session.flush()
        return collection

    if restore_if_deleted and collection.deleted_at is not None:
        collection.deleted_at = None
        collection.updated_at = utc_now()
        session.add(collection)
        await session.flush()

    return collection


async def read_menu_items(
    session: AsyncSession,
    *,
    menu_group: str | None = None,
    section: str | None = None,
    search: str | None = None,
    available_only: bool = False,
    unavailable_only: bool = False,
    deleted_only: bool = False,
) -> list[MenuEntryRecord]:
    statement = select(MenuEntryRecord)

    if deleted_only:
        statement = statement.where(MenuEntryRecord.deleted_at.is_not(None))
    else:
        statement = statement.where(MenuEntryRecord.deleted_at.is_(None))

    if menu_group:
        statement = statement.where(MenuEntryRecord.menu_group == menu_group)

    if section:
        statement = statement.where(MenuEntryRecord.section == section)

    if search:
        pattern = f"%{search.lower()}%"
        statement = statement.where(
            or_(
                func.lower(MenuEntryRecord.name).like(pattern),
                func.lower(MenuEntryRecord.name_en).like(pattern),
                func.lower(MenuEntryRecord.description).like(pattern),
                func.lower(MenuEntryRecord.description_en).like(pattern),
                func.lower(MenuEntryRecord.ingredients).like(pattern),
                func.lower(MenuEntryRecord.ingredients_en).like(pattern),
                func.lower(MenuEntryRecord.section).like(pattern),
                func.lower(MenuEntryRecord.menu_group).like(pattern),
            )
        )

    if available_only:
        statement = statement.where(MenuEntryRecord.is_available.is_(True))
    elif unavailable_only:
        statement = statement.where(MenuEntryRecord.is_available.is_(False))

    statement = statement.order_by(
        MenuEntryRecord.deleted_at.desc(),
        MenuEntryRecord.updated_at.desc(),
        MenuEntryRecord.created_at.desc(),
        MenuEntryRecord.id.desc(),
    )

    result = await session.exec(statement)
    return list(result.all())


async def read_menu_item(
    session: AsyncSession,
    item_id: int,
    *,
    include_deleted: bool = False,
) -> MenuEntryRecord | None:
    item = await session.get(MenuEntryRecord, item_id)
    if item is None:
        return None
    if not include_deleted and item.deleted_at is not None:
        return None
    return item


async def read_menu_groups(session: AsyncSession) -> list[str]:
    statement = (
        select(MenuCollectionRecord.name)
        .where(MenuCollectionRecord.deleted_at.is_(None))
        .order_by(
            MenuCollectionRecord.updated_at.desc(),
            MenuCollectionRecord.created_at.desc(),
            MenuCollectionRecord.name.asc(),
        )
    )
    result = await session.exec(statement)
    return list(result.all())


async def read_menu_catalog(session: AsyncSession) -> list[MenuCollectionSummary]:
    count_statement = (
        select(
            MenuEntryRecord.menu_group,
            func.sum(
                case((MenuEntryRecord.deleted_at.is_(None), 1), else_=0)
            ).label("active_items"),
            func.sum(
                case((MenuEntryRecord.deleted_at.is_not(None), 1), else_=0)
            ).label("deleted_items"),
        )
        .group_by(MenuEntryRecord.menu_group)
    )
    count_rows = await session.exec(count_statement)
    item_counts = {
        row[0]: {
            "active_items": int(row[1] or 0),
            "deleted_items": int(row[2] or 0),
        }
        for row in count_rows.all()
    }

    statement = (
        select(MenuCollectionRecord)
        .order_by(
            MenuCollectionRecord.deleted_at.is_not(None),
            MenuCollectionRecord.updated_at.desc(),
            MenuCollectionRecord.created_at.desc(),
            MenuCollectionRecord.name.asc(),
        )
    )
    result = await session.exec(statement)
    collections = list(result.all())

    return [
        MenuCollectionSummary(
            id=collection.id or 0,
            name=collection.name,
            created_at=collection.created_at,
            updated_at=collection.updated_at,
            deleted_at=collection.deleted_at,
            active_items=item_counts.get(collection.name, {}).get("active_items", 0),
            deleted_items=item_counts.get(collection.name, {}).get("deleted_items", 0),
        )
        for collection in collections
    ]


async def read_sections(
    session: AsyncSession,
    *,
    menu_group: str | None = None,
) -> list[str]:
    statement = select(MenuEntryRecord.section).distinct().where(
        MenuEntryRecord.deleted_at.is_(None)
    )
    if menu_group:
        statement = statement.where(MenuEntryRecord.menu_group == menu_group)
    statement = statement.order_by(MenuEntryRecord.section)
    result = await session.exec(statement)
    return list(result.all())


async def create_menu_collection(
    session: AsyncSession,
    payload: MenuCollectionCreate,
) -> MenuCollectionRecord | None:
    normalized_name = payload.name.strip()
    existing_statement = select(MenuCollectionRecord).where(
        MenuCollectionRecord.name == normalized_name
    )
    existing = (await session.exec(existing_statement)).first()
    if existing is not None:
        return None

    collection = MenuCollectionRecord(name=normalized_name)
    session.add(collection)
    await session.commit()
    await session.refresh(collection)
    return collection


async def restore_menu_collection(
    session: AsyncSession,
    menu_id: int,
) -> MenuCollectionRecord | None:
    collection = await session.get(MenuCollectionRecord, menu_id)
    if collection is None:
        return None

    timestamp = utc_now()
    collection.deleted_at = None
    collection.updated_at = timestamp
    session.add(collection)

    items_statement = select(MenuEntryRecord).where(
        MenuEntryRecord.menu_group == collection.name,
        MenuEntryRecord.deleted_at.is_not(None),
        MenuEntryRecord.deleted_via_menu.is_(True),
    )
    items = list((await session.exec(items_statement)).all())
    for item in items:
        item.deleted_at = None
        item.deleted_via_menu = False
        item.updated_at = timestamp
        session.add(item)

    await session.commit()
    await session.refresh(collection)
    invalidate_menu_render_cache()
    return collection


async def delete_menu_collection(session: AsyncSession, menu_id: int) -> bool:
    collection = await session.get(MenuCollectionRecord, menu_id)
    if collection is None or collection.deleted_at is not None:
        return False

    timestamp = utc_now()
    collection.deleted_at = timestamp
    collection.updated_at = timestamp
    session.add(collection)

    items_statement = select(MenuEntryRecord).where(
        MenuEntryRecord.menu_group == collection.name,
        MenuEntryRecord.deleted_at.is_(None),
    )
    items = list((await session.exec(items_statement)).all())
    for item in items:
        item.deleted_at = timestamp
        item.deleted_via_menu = True
        item.updated_at = timestamp
        session.add(item)

    await session.commit()
    invalidate_menu_render_cache()
    return True


async def create_menu_item(
    session: AsyncSession,
    payload: MenuEntryCreate,
) -> MenuEntryRecord:
    normalized_payload = ensure_secondary_language_fields(payload.model_dump(mode="json"))
    await ensure_menu_collection(
        session,
        normalized_payload["menu_group"],
        restore_if_deleted=True,
    )
    item = MenuEntryRecord.model_validate(normalized_payload)
    session.add(item)
    await session.commit()
    await session.refresh(item)
    invalidate_menu_render_cache()
    return item


async def update_menu_item(
    session: AsyncSession,
    item_id: int,
    payload: MenuEntryUpdate,
) -> MenuEntryRecord | None:
    item = await read_menu_item(session, item_id)
    if item is None:
        return None

    normalized_payload = ensure_secondary_language_fields(payload.model_dump(mode="json"))
    await ensure_menu_collection(
        session,
        normalized_payload["menu_group"],
        restore_if_deleted=True,
    )

    for field_name, value in normalized_payload.items():
        setattr(item, field_name, value)

    item.updated_at = utc_now()
    session.add(item)
    await session.commit()
    await session.refresh(item)
    invalidate_menu_render_cache()
    return item


async def set_menu_item_availability(
    session: AsyncSession,
    item_id: int,
    *,
    is_available: bool,
) -> MenuEntryRecord | None:
    item = await read_menu_item(session, item_id)
    if item is None:
        return None

    item.is_available = is_available
    item.updated_at = utc_now()
    session.add(item)
    await session.commit()
    await session.refresh(item)
    invalidate_menu_render_cache()
    return item


async def delete_menu_item(session: AsyncSession, item_id: int) -> bool:
    item = await read_menu_item(session, item_id)
    if item is None:
        return False

    timestamp = utc_now()
    item.deleted_at = timestamp
    item.deleted_via_menu = False
    item.updated_at = timestamp
    session.add(item)
    await session.commit()
    invalidate_menu_render_cache()
    return True


async def restore_menu_item(
    session: AsyncSession,
    item_id: int,
) -> MenuEntryRecord | None:
    item = await read_menu_item(session, item_id, include_deleted=True)
    if item is None or item.deleted_at is None:
        return None

    await ensure_menu_collection(session, item.menu_group, restore_if_deleted=True)
    item.deleted_at = None
    item.deleted_via_menu = False
    item.updated_at = utc_now()
    session.add(item)
    await session.commit()
    await session.refresh(item)
    invalidate_menu_render_cache()
    return item


async def read_menu_summary(session: AsyncSession) -> MenuSummary:
    items = await read_menu_items(session)
    groups = await read_menu_groups(session)

    last_updated_at = max((item.updated_at for item in items), default=None)
    return MenuSummary(
        total_items=len(items),
        available_items=sum(1 for item in items if item.is_available),
        featured_items=sum(1 for item in items if item.is_featured),
        menu_groups=len(groups),
        sections=len({item.section for item in items}),
        last_updated_at=last_updated_at,
    )
