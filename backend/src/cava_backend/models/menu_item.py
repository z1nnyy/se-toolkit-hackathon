from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from pydantic import field_validator
from sqlalchemy import JSON, Column, String
from sqlmodel import Field, SQLModel


def utc_now() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


class MenuVariant(SQLModel):
    portion: str = Field(min_length=1, max_length=40)
    price: float = Field(ge=0)
    label: str = Field(default="", max_length=40)


class MenuEntryBase(SQLModel):
    name: str = Field(min_length=1, max_length=160)
    name_en: str = Field(default="", max_length=160)
    menu_group: str = Field(min_length=1, max_length=80, index=True)
    section: str = Field(min_length=1, max_length=80, index=True)
    description: str = Field(default="", max_length=240)
    description_en: str = Field(default="", max_length=240)
    ingredients: str = Field(default="", max_length=800)
    ingredients_en: str = Field(default="", max_length=800)
    image_url: str = Field(default="", max_length=500)
    tags: list[str] = Field(default_factory=list)
    variants: list[MenuVariant] = Field(default_factory=list)
    is_available: bool = True
    is_featured: bool = False
    position: int = Field(default=0, ge=0)

    @field_validator("variants")
    @classmethod
    def validate_variants(cls, value: list[MenuVariant]) -> list[MenuVariant]:
        if not value:
            raise ValueError("At least one portion/price variant is required.")
        return value


class MenuEntryRecord(SQLModel, table=True):
    __tablename__ = "menu_entry"

    id: int | None = Field(default=None, primary_key=True)
    name: str = Field(min_length=1, max_length=160)
    name_en: str = Field(default="", max_length=160)
    menu_group: str = Field(min_length=1, max_length=80, index=True)
    section: str = Field(min_length=1, max_length=80, index=True)
    description: str = Field(default="", max_length=240)
    description_en: str = Field(default="", max_length=240)
    ingredients: str = Field(default="", max_length=800)
    ingredients_en: str = Field(default="", max_length=800)
    image_url: str = Field(default="", max_length=500)
    tags: list[str] = Field(
        default_factory=list,
        sa_column=Column(JSON, nullable=False),
    )
    variants: list[dict[str, Any]] = Field(
        default_factory=list,
        sa_column=Column(JSON, nullable=False),
    )
    is_available: bool = True
    is_featured: bool = False
    position: int = Field(default=0, ge=0)
    deleted_at: datetime | None = None
    deleted_via_menu: bool = False
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)


class MenuEntryCreate(MenuEntryBase):
    pass


class MenuEntryUpdate(MenuEntryBase):
    pass


class MenuItemAvailabilityUpdate(SQLModel):
    is_available: bool


class MenuCollectionBase(SQLModel):
    name: str = Field(min_length=1, max_length=80)


class MenuCollectionRecord(SQLModel, table=True):
    __tablename__ = "menu_collection"

    id: int | None = Field(default=None, primary_key=True)
    name: str = Field(
        sa_column=Column(String(80), unique=True, nullable=False, index=True)
    )
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)
    deleted_at: datetime | None = None


class MenuCollectionCreate(MenuCollectionBase):
    pass


class MenuCollectionSummary(SQLModel):
    id: int
    name: str
    created_at: datetime
    updated_at: datetime
    deleted_at: datetime | None = None
    active_items: int = 0
    deleted_items: int = 0


class MenuSummary(SQLModel):
    total_items: int
    available_items: int
    featured_items: int
    menu_groups: int
    sections: int
    last_updated_at: datetime | None = None


class MenuPoster(SQLModel):
    id: str
    title: str
    description: str
    asset_path: str
    groups: list[str] = Field(default_factory=list)


class MenuRenderPage(SQLModel):
    page: int
    title: str


class MenuRenderManifest(SQLModel):
    total_pages: int
    pages: list[MenuRenderPage] = Field(default_factory=list)
