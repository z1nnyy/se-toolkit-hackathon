from __future__ import annotations

from collections.abc import AsyncGenerator
from datetime import datetime, timezone
from pathlib import Path

from sqlalchemy import inspect, text
from sqlalchemy.ext.asyncio import create_async_engine
from sqlmodel import SQLModel
from sqlmodel.ext.asyncio.session import AsyncSession

from cava_backend.settings import settings


SQLITE_PREFIX = "sqlite+aiosqlite:///"


def _sqlite_connect_args() -> dict[str, bool]:
    if settings.database_url.startswith("sqlite"):
        return {"check_same_thread": False}
    return {}


def _ensure_database_parent_dir() -> None:
    if not settings.database_url.startswith(SQLITE_PREFIX):
        return

    database_path = settings.database_url.removeprefix(SQLITE_PREFIX)
    if not database_path or database_path == ":memory:":
        return

    Path(database_path).expanduser().resolve().parent.mkdir(parents=True, exist_ok=True)


engine = create_async_engine(
    settings.database_url,
    echo=settings.debug,
    connect_args=_sqlite_connect_args(),
)


MENU_ENTRY_MIGRATIONS = {
    "name_en": "ALTER TABLE menu_entry ADD COLUMN name_en VARCHAR(160) NOT NULL DEFAULT ''",
    "description_en": "ALTER TABLE menu_entry ADD COLUMN description_en VARCHAR(240) NOT NULL DEFAULT ''",
    "ingredients_en": "ALTER TABLE menu_entry ADD COLUMN ingredients_en VARCHAR(800) NOT NULL DEFAULT ''",
    "deleted_at": "ALTER TABLE menu_entry ADD COLUMN deleted_at DATETIME",
    "deleted_via_menu": "ALTER TABLE menu_entry ADD COLUMN deleted_via_menu BOOLEAN NOT NULL DEFAULT 0",
}


def _migrate_menu_entry_table(connection) -> None:
    inspector = inspect(connection)
    if "menu_entry" not in inspector.get_table_names():
        return

    existing_columns = {
        column["name"]
        for column in inspector.get_columns("menu_entry")
    }
    for column_name, ddl in MENU_ENTRY_MIGRATIONS.items():
        if column_name in existing_columns:
            continue
        connection.execute(text(ddl))


def _migrate_menu_collection_table(connection) -> None:
    inspector = inspect(connection)
    if "menu_collection" not in inspector.get_table_names():
        return

    existing_columns = {
        column["name"]
        for column in inspector.get_columns("menu_collection")
    }
    if "deleted_at" not in existing_columns:
        connection.execute(
            text("ALTER TABLE menu_collection ADD COLUMN deleted_at DATETIME")
        )


def _sync_menu_collections_from_items(connection) -> None:
    inspector = inspect(connection)
    table_names = set(inspector.get_table_names())
    if "menu_entry" not in table_names or "menu_collection" not in table_names:
        return

    known_names = {
        row[0]
        for row in connection.execute(text("SELECT name FROM menu_collection")).fetchall()
    }
    menu_names = [
        row[0]
        for row in connection.execute(
            text(
                "SELECT DISTINCT menu_group FROM menu_entry "
                "WHERE menu_group IS NOT NULL AND TRIM(menu_group) != ''"
            )
        ).fetchall()
    ]
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    for name in menu_names:
        if name in known_names:
            continue

        active_count = connection.execute(
            text(
                "SELECT COUNT(*) FROM menu_entry "
                "WHERE menu_group = :menu_group AND deleted_at IS NULL"
            ),
            {"menu_group": name},
        ).scalar_one()
        last_deleted_at = connection.execute(
            text(
                "SELECT MAX(deleted_at) FROM menu_entry "
                "WHERE menu_group = :menu_group"
            ),
            {"menu_group": name},
        ).scalar_one_or_none()
        connection.execute(
            text(
                "INSERT INTO menu_collection (name, created_at, updated_at, deleted_at) "
                "VALUES (:name, :created_at, :updated_at, :deleted_at)"
            ),
            {
                "name": name,
                "created_at": now,
                "updated_at": now,
                "deleted_at": None if active_count else last_deleted_at,
            },
        )


async def init_database() -> None:
    _ensure_database_parent_dir()

    async with engine.begin() as connection:
        await connection.run_sync(SQLModel.metadata.create_all)
        await connection.run_sync(_migrate_menu_entry_table)
        await connection.run_sync(_migrate_menu_collection_table)
        await connection.run_sync(_sync_menu_collections_from_items)


async def get_session() -> AsyncGenerator[AsyncSession, None]:
    async with AsyncSession(engine) as session:
        yield session
