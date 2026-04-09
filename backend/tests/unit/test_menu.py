from __future__ import annotations

from datetime import datetime
from io import BytesIO
from pathlib import Path

import pytest
from httpx import ASGITransport, AsyncClient
from PIL import Image, ImageDraw
from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine
from sqlmodel import SQLModel
from sqlmodel.ext.asyncio.session import AsyncSession

from cava_backend.auth import hash_password
from cava_backend.database import get_session
from cava_backend.main import app
from cava_backend.models.menu_item import MenuCollectionRecord, MenuEntryRecord
from cava_backend.models.user import AppUserRecord
from cava_backend.services.menu_image_renderer import (
    _badge_block_height,
    _build_card_height,
    _build_config,
    _build_fonts,
    _build_item_layout,
    _build_section_title_lines,
    _measure_text,
    _multiline_height,
    _section_header_height,
    _wrap_text,
    render_menu_image,
)
from cava_backend.services.menu_localization import (
    ensure_secondary_language_fields,
    translate_menu_text,
)
from cava_backend.services.menu_render_cache import (
    get_menu_render_cache_dir,
    get_menu_render_cache_path,
    invalidate_menu_render_cache,
)
from cava_backend.settings import settings


@pytest.fixture
async def engine(tmp_path: Path) -> AsyncEngine:
    db_path = tmp_path / "test-menu.db"
    engine = create_async_engine(
        f"sqlite+aiosqlite:///{db_path}",
        connect_args={"check_same_thread": False},
    )

    async with engine.begin() as connection:
        await connection.run_sync(SQLModel.metadata.create_all)

    yield engine

    await engine.dispose()


@pytest.fixture
async def seed_data(engine: AsyncEngine) -> None:
    async with AsyncSession(engine) as session:
        super_admin_salt, super_admin_hash = hash_password("owner12345")
        staff_salt, staff_hash = hash_password("barista123")
        session.add_all(
            [
                AppUserRecord(
                    id=1,
                    username="owner",
                    full_name="Main Administrator",
                    role="super_admin",
                    password_salt=super_admin_salt,
                    password_hash=super_admin_hash,
                    is_active=True,
                    created_at=datetime(2026, 4, 1, 9, 50),
                    last_login_at=None,
                ),
                AppUserRecord(
                    id=2,
                    username="barista_anna",
                    full_name="Anna Petrova",
                    role="staff_admin",
                    password_salt=staff_salt,
                    password_hash=staff_hash,
                    is_active=True,
                    created_at=datetime(2026, 4, 1, 9, 55),
                    last_login_at=None,
                ),
                MenuCollectionRecord(
                    id=1,
                    name="Основное меню",
                    created_at=datetime(2026, 4, 1, 9, 56),
                    updated_at=datetime(2026, 4, 1, 10, 0),
                    deleted_at=None,
                ),
                MenuCollectionRecord(
                    id=2,
                    name="Весеннее меню",
                    created_at=datetime(2026, 4, 1, 9, 57),
                    updated_at=datetime(2026, 4, 1, 10, 5),
                    deleted_at=None,
                ),
                MenuCollectionRecord(
                    id=3,
                    name="Пицца",
                    created_at=datetime(2026, 4, 1, 9, 58),
                    updated_at=datetime(2026, 4, 1, 10, 10),
                    deleted_at=None,
                ),
                MenuEntryRecord(
                    id=1,
                    name="Капучино",
                    name_en="Cappuccino",
                    menu_group="Основное меню",
                    section="Кофе",
                    description="Молочный кофе",
                    description_en="Milk coffee",
                    ingredients="Эспрессо, молоко, молочная пена",
                    ingredients_en="Espresso, milk, milk foam",
                    variants=[{"portion": "250 мл", "price": 230, "label": ""}],
                    tags=["signature"],
                    is_available=True,
                    is_featured=True,
                    position=1,
                    deleted_at=None,
                    deleted_via_menu=False,
                    created_at=datetime(2026, 4, 1, 10, 0),
                    updated_at=datetime(2026, 4, 1, 10, 0),
                ),
                MenuEntryRecord(
                    id=2,
                    name="Матча латте",
                    name_en="Matcha Latte",
                    menu_group="Весеннее меню",
                    section="Весеннее меню",
                    description="Сезонный напиток",
                    description_en="Seasonal drink",
                    ingredients="Матча, молоко",
                    ingredients_en="Matcha, milk",
                    variants=[{"portion": "350 мл", "price": 290, "label": ""}],
                    tags=["seasonal"],
                    is_available=False,
                    is_featured=False,
                    position=1,
                    deleted_at=None,
                    deleted_via_menu=False,
                    created_at=datetime(2026, 4, 1, 10, 5),
                    updated_at=datetime(2026, 4, 1, 10, 5),
                ),
                MenuEntryRecord(
                    id=3,
                    name="Пепперони",
                    name_en="Pepperoni",
                    menu_group="Пицца",
                    section="Пицца",
                    description="Острая пицца",
                    description_en="Spicy pizza",
                    ingredients="Моцарелла, томатный соус, пепперони",
                    ingredients_en="Mozzarella, tomato sauce, pepperoni",
                    variants=[{"portion": "520 гр", "price": 580, "label": ""}],
                    tags=[],
                    is_available=True,
                    is_featured=False,
                    position=1,
                    deleted_at=None,
                    deleted_via_menu=False,
                    created_at=datetime(2026, 4, 1, 10, 10),
                    updated_at=datetime(2026, 4, 1, 10, 10),
                ),
            ]
        )
        await session.commit()


@pytest.fixture
async def client(engine: AsyncEngine, seed_data: None) -> AsyncClient:
    async def override_session():
        async with AsyncSession(engine) as session:
            yield session

    app.dependency_overrides[get_session] = override_session

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client

    app.dependency_overrides.clear()


@pytest.fixture(autouse=True)
def clean_render_cache(tmp_path: Path) -> None:
    settings.menu_render_cache_dir = str(tmp_path / "menu-render-cache")
    invalidate_menu_render_cache()
    yield
    invalidate_menu_render_cache()


async def login_and_get_headers(
    client: AsyncClient,
    *,
    username: str,
    password: str,
) -> dict[str, str]:
    response = await client.post(
        "/auth/login",
        json={
            "username": username,
            "password": password,
        },
    )
    assert response.status_code == 200
    access_token = response.json()["access_token"]
    return {"Authorization": f"Bearer {access_token}"}


@pytest.mark.asyncio
async def test_healthcheck_returns_ok(client: AsyncClient) -> None:
    response = await client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


@pytest.mark.asyncio
async def test_get_menu_items_can_filter_by_group_and_availability(
    client: AsyncClient,
) -> None:
    response = await client.get(
        "/menu/items",
        params={"menu_group": "Пицца", "available_only": "true"},
    )
    data = response.json()

    assert response.status_code == 200
    assert len(data) == 1
    assert data[0]["name"] == "Пепперони"

    english_search_response = await client.get("/menu/items", params={"search": "milk coffee"})
    english_search_data = english_search_response.json()
    assert english_search_response.status_code == 200
    assert len(english_search_data) == 1
    assert english_search_data[0]["name_en"] == "Cappuccino"

    unavailable_response = await client.get(
        "/menu/items",
        params={"unavailable_only": "true"},
    )
    unavailable_data = unavailable_response.json()
    assert unavailable_response.status_code == 200
    assert len(unavailable_data) == 1
    assert unavailable_data[0]["name"] == "Матча латте"


@pytest.mark.asyncio
async def test_menu_metadata_endpoints_return_expected_values(
    client: AsyncClient,
) -> None:
    groups_response = await client.get("/menu/groups")
    sections_response = await client.get("/menu/sections")
    posters_response = await client.get("/menu/posters")
    render_response = await client.get(
        "/menu/render",
        params={"menu_group": "Пицца", "language": "en", "width": "1200"},
    )

    assert groups_response.status_code == 200
    assert set(groups_response.json()) == {"Весеннее меню", "Основное меню", "Пицца"}

    assert sections_response.status_code == 200
    assert "Кофе" in sections_response.json()
    assert "Пицца" in sections_response.json()

    assert posters_response.status_code == 200
    assert len(posters_response.json()) >= 4

    assert render_response.status_code == 200
    assert render_response.headers["content-type"].startswith("image/png")
    assert render_response.content.startswith(b"\x89PNG\r\n\x1a\n")


@pytest.mark.asyncio
async def test_menu_render_is_cached_and_invalidated_after_menu_change(
    client: AsyncClient,
) -> None:
    cache_path = get_menu_render_cache_path(
        language="ru",
        menu_group=None,
        section=None,
        available_only=False,
        width=1200,
    )
    assert get_menu_render_cache_dir().exists()
    assert not cache_path.exists()

    first_render = await client.get(
        "/menu/render",
        params={"language": "ru", "width": "1200"},
    )
    assert first_render.status_code == 200
    assert cache_path.exists()
    cached_bytes_before = cache_path.read_bytes()
    assert cached_bytes_before == first_render.content

    headers = await login_and_get_headers(
        client,
        username="owner",
        password="owner12345",
    )
    update_response = await client.put(
        "/menu/items/1",
        headers=headers,
        json={
            "name": "Капучино XXL",
            "name_en": "Cappuccino XXL",
            "menu_group": "Основное меню",
            "section": "Кофе",
            "description": "Обновленный молочный кофе",
            "description_en": "Updated milk coffee",
            "ingredients": "Эспрессо, молоко, молочная пена",
            "ingredients_en": "Espresso, milk, milk foam",
            "image_url": "",
            "tags": ["signature"],
            "variants": [{"portion": "250 мл", "price": 230, "label": ""}],
            "is_available": True,
            "is_featured": True,
            "position": 1,
        },
    )
    assert update_response.status_code == 200
    assert not cache_path.exists()

    second_render = await client.get(
        "/menu/render",
        params={"language": "ru", "width": "1200"},
    )
    assert second_render.status_code == 200
    assert cache_path.exists()
    cached_bytes_after = cache_path.read_bytes()
    assert cached_bytes_after == second_render.content
    assert cached_bytes_after != cached_bytes_before


def test_menu_card_height_matches_actual_rendered_content() -> None:
    config = _build_config(1600)
    fonts = _build_fonts(config.width)
    draw = ImageDraw.Draw(Image.new("RGB", (config.width, config.height)))

    items = [
        MenuEntryRecord(
            id=10,
            name="Фермерский завтрак",
            name_en="Farmer Breakfast",
            menu_group="Основное меню",
            section="Завтраки",
            description="Курино-говяжья колбаска, глазунья, картофельные дольки, соус сладкий чили.",
            description_en="Chicken-beef sausage, fried eggs, potato wedges, sweet chili sauce.",
            ingredients="Колбаска, яйцо, картофель, соус.",
            ingredients_en="Sausage, egg, potato, sauce.",
            variants=[{"portion": "300 гр", "price": 420, "label": ""}],
            tags=[],
            is_available=True,
            is_featured=False,
            position=1,
            deleted_at=None,
            deleted_via_menu=False,
            created_at=datetime(2026, 4, 1, 10, 0),
            updated_at=datetime(2026, 4, 1, 10, 0),
        ),
        MenuEntryRecord(
            id=11,
            name="Мексиканская торта",
            name_en="Mexican Torta",
            menu_group="Основное меню",
            section="Завтраки",
            description="Чиабатта, колбаска чоризо, рикотта, авокадо, огурцы, красный лук, чеснок, кинза.",
            description_en="Ciabatta, chorizo sausage, ricotta, avocado, cucumbers, red onion, garlic, cilantro.",
            ingredients="Чиабатта, чоризо, рикотта, авокадо.",
            ingredients_en="Ciabatta, chorizo, ricotta, avocado.",
            variants=[{"portion": "200 гр", "price": 350, "label": ""}],
            tags=[],
            is_available=True,
            is_featured=True,
            position=2,
            deleted_at=None,
            deleted_via_menu=False,
            created_at=datetime(2026, 4, 1, 10, 5),
            updated_at=datetime(2026, 4, 1, 10, 5),
        ),
        MenuEntryRecord(
            id=12,
            name="Овсяная каша",
            name_en="Oatmeal",
            menu_group="Основное меню",
            section="Завтраки",
            description="Каша на молоке с яблоком, изюмом или вареньем.",
            description_en="Milk porridge with apple, raisins, or jam.",
            ingredients="Овсяные хлопья, молоко, яблоко.",
            ingredients_en="Oats, milk, apple.",
            variants=[{"portion": "250 гр", "price": 220, "label": ""}],
            tags=[],
            is_available=False,
            is_featured=False,
            position=3,
            deleted_at=None,
            deleted_via_menu=False,
            created_at=datetime(2026, 4, 1, 10, 10),
            updated_at=datetime(2026, 4, 1, 10, 10),
        ),
    ]

    title_lines = _build_section_title_lines(
        "Завтраки",
        continued=False,
        draw=draw,
        config=config,
        fonts=fonts,
        language="ru",
    )
    item_layouts = [
        _build_item_layout(item, draw, config, fonts, "ru")
        for item in items
    ]
    computed_height = _build_card_height(draw, title_lines, item_layouts, config, fonts)

    header_height = _section_header_height(draw, title_lines, config, fonts)
    cursor_y = header_height + config.card_padding - 6
    for item_layout in item_layouts:
        if item_layout.is_featured:
            cursor_y += _badge_block_height(draw, fonts.section_tag)
        if not item_layout.is_available:
            cursor_y += _badge_block_height(draw, fonts.section_tag)
        cursor_y += _multiline_height(
            draw,
            item_layout.name_lines,
            fonts.item_name,
            spacing=config.body_spacing,
        ) + 8
        cursor_y += _multiline_height(
            draw,
            item_layout.variant_lines,
            fonts.item_meta,
            spacing=config.note_spacing,
        ) + 8
        if item_layout.note_lines:
            cursor_y += _multiline_height(
                draw,
                item_layout.note_lines,
                fonts.item_note,
                spacing=config.note_spacing,
            )
        cursor_y += config.item_gap

    actual_height = config.card_padding + cursor_y
    assert computed_height == actual_height


def test_wrap_text_breaks_long_tokens_to_fit_width() -> None:
    config = _build_config(900)
    fonts = _build_fonts(config.width)
    draw = ImageDraw.Draw(Image.new("RGB", (config.width, config.height)))

    lines = _wrap_text(
        draw,
        "Суперультрамегадлинноеблюдоспециальнодляпроверкипереносатекста",
        fonts.item_name,
        180,
    )

    assert lines
    assert all(_measure_text(draw, line, fonts.item_name) <= 180 for line in lines)


def test_translate_menu_text_generates_readable_english() -> None:
    assert (
        translate_menu_text(
            "Грибной сэндвич с баклажанами",
            context="name",
        )
        == "Mushroom Sandwich with Eggplant"
    )
    assert translate_menu_text("Фо бо / Фо га", context="name") == "Pho Bo / Pho Ga"
    assert (
        translate_menu_text(
            "Моцарелла, соус тейсти, говяжий фарш, томаты, красный лук",
            context="ingredients",
        )
        == "Mozzarella, Tasty sauce, ground beef, tomatoes, red onion"
    )
    assert (
        translate_menu_text("Сезонная позиция", context="description")
        == "Seasonal item"
    )


def test_ensure_secondary_language_fields_autofills_english_versions() -> None:
    localized = ensure_secondary_language_fields(
        {
            "name": "Грибной сэндвич с баклажанами",
            "name_en": "",
            "description": "Сезонная позиция",
            "description_en": "",
            "ingredients": "Чиабатта, баклажаны, шампиньоны, сливки",
            "ingredients_en": "",
        }
    )

    assert localized["name_en"] == "Mushroom Sandwich with Eggplant"
    assert localized["description_en"] == "Seasonal item"
    assert localized["ingredients_en"] == "Ciabatta, eggplant, champignons, cream"


def test_single_page_render_prefers_horizontal_layout_for_large_menu() -> None:
    items = [
        MenuEntryRecord(
            id=index,
            name=f"Позиция {index}",
            name_en=f"Item {index}",
            menu_group="Основное меню",
            section=f"Раздел {((index - 1) // 8) + 1}",
            description="",
            description_en="",
            ingredients="Ингредиенты блюда для проверки макета.",
            ingredients_en="Ingredients for layout verification.",
            variants=[{"portion": "300 гр", "price": 300 + index, "label": ""}],
            tags=[],
            is_available=True,
            is_featured=index % 7 == 0,
            position=index,
            deleted_at=None,
            deleted_via_menu=False,
            created_at=datetime(2026, 4, 1, 10, 0),
            updated_at=datetime(2026, 4, 1, 10, 0),
        )
        for index in range(1, 49)
    ]

    image = Image.open(BytesIO(render_menu_image(items, width=5000, single_page=True)))
    assert image.width == 5000
    assert image.width / image.height > 0.8


def test_single_page_render_reduces_extra_vertical_space_for_small_menu() -> None:
    items = [
        MenuEntryRecord(
            id=1,
            name="Эспрессо",
            name_en="Espresso",
            menu_group="Основное меню",
            section="Кофе",
            description="",
            description_en="",
            ingredients="Классический эспрессо.",
            ingredients_en="Classic espresso.",
            variants=[{"portion": "40 мл", "price": 160, "label": ""}],
            tags=[],
            is_available=True,
            is_featured=False,
            position=1,
            deleted_at=None,
            deleted_via_menu=False,
            created_at=datetime(2026, 4, 1, 10, 0),
            updated_at=datetime(2026, 4, 1, 10, 0),
        ),
        MenuEntryRecord(
            id=2,
            name="Американо",
            name_en="Americano",
            menu_group="Основное меню",
            section="Кофе",
            description="",
            description_en="",
            ingredients="Эспрессо и горячая вода.",
            ingredients_en="Espresso and hot water.",
            variants=[{"portion": "200 мл", "price": 180, "label": ""}],
            tags=[],
            is_available=True,
            is_featured=False,
            position=2,
            deleted_at=None,
            deleted_via_menu=False,
            created_at=datetime(2026, 4, 1, 10, 0),
            updated_at=datetime(2026, 4, 1, 10, 0),
        ),
    ]

    image = Image.open(BytesIO(render_menu_image(items, width=1600, single_page=True)))
    assert image.height < 1600


@pytest.mark.asyncio
async def test_admin_can_create_update_toggle_delete_and_restore_item(
    client: AsyncClient,
) -> None:
    headers = await login_and_get_headers(
        client,
        username="owner",
        password="owner12345",
    )

    create_response = await client.post(
        "/menu/items",
        headers=headers,
        json={
            "name": "Грибной сэндвич",
            "menu_group": "Весеннее меню",
            "section": "Весеннее меню",
            "description": "Сезонная позиция",
            "ingredients": "Чиабатта, баклажаны, шампиньоны",
            "image_url": "",
            "tags": ["seasonal"],
            "variants": [{"portion": "390 гр", "price": 450, "label": ""}],
            "is_available": True,
            "is_featured": False,
            "position": 3,
        },
    )
    assert create_response.status_code == 201
    created_item = create_response.json()
    assert created_item["variants"][0]["price"] == 450
    assert created_item["name_en"] == "Mushroom Sandwich"
    assert created_item["description_en"] == "Seasonal item"
    assert created_item["ingredients_en"] == "Ciabatta, eggplant, champignons"

    update_response = await client.put(
        f"/menu/items/{created_item['id']}",
        headers=headers,
        json={
            "name": "Грибной сэндвич с баклажанами",
            "name_en": "Mushroom Sandwich with Eggplant",
            "menu_group": "Весеннее меню",
            "section": "Весеннее меню",
            "description": "Сезонный хит",
            "description_en": "Seasonal favorite",
            "ingredients": "Чиабатта, баклажаны, шампиньоны, сливки",
            "ingredients_en": "Ciabatta, eggplant, champignons, cream",
            "image_url": "https://example.com/sandwich.png",
            "tags": ["seasonal", "new"],
            "variants": [{"portion": "390 гр", "price": 470, "label": ""}],
            "is_available": True,
            "is_featured": True,
            "position": 2,
        },
    )
    assert update_response.status_code == 200
    assert update_response.json()["name"] == "Грибной сэндвич с баклажанами"
    assert update_response.json()["name_en"] == "Mushroom Sandwich with Eggplant"
    assert update_response.json()["variants"][0]["price"] == 470

    patch_response = await client.patch(
        f"/menu/items/{created_item['id']}/availability",
        headers=headers,
        json={"is_available": False},
    )
    assert patch_response.status_code == 200
    assert patch_response.json()["is_available"] is False

    delete_response = await client.delete(
        f"/menu/items/{created_item['id']}",
        headers=headers,
    )
    assert delete_response.status_code == 204

    deleted_items_response = await client.get("/menu/items", params={"deleted_only": "true"})
    assert deleted_items_response.status_code == 200
    assert any(item["id"] == created_item["id"] for item in deleted_items_response.json())

    restore_response = await client.post(
        f"/menu/items/{created_item['id']}/restore",
        headers=headers,
    )
    assert restore_response.status_code == 200
    assert restore_response.json()["deleted_at"] is None


@pytest.mark.asyncio
async def test_admin_can_create_delete_and_restore_menu_collection(
    client: AsyncClient,
) -> None:
    headers = await login_and_get_headers(
        client,
        username="owner",
        password="owner12345",
    )

    create_menu_response = await client.post(
        "/menu/catalog",
        headers=headers,
        json={"name": "Летнее меню"},
    )
    assert create_menu_response.status_code == 201
    created_menu = create_menu_response.json()
    assert created_menu["name"] == "Летнее меню"

    delete_menu_response = await client.delete(
        f"/menu/catalog/{created_menu['id']}",
        headers=headers,
    )
    assert delete_menu_response.status_code == 204

    catalog_response = await client.get("/menu/catalog")
    assert catalog_response.status_code == 200
    deleted_menu = next(
        item for item in catalog_response.json() if item["id"] == created_menu["id"]
    )
    assert deleted_menu["deleted_at"] is not None

    restore_menu_response = await client.post(
        f"/menu/catalog/{created_menu['id']}/restore",
        headers=headers,
    )
    assert restore_menu_response.status_code == 200
    assert restore_menu_response.json()["deleted_at"] is None


@pytest.mark.asyncio
async def test_admin_requests_require_authorization(client: AsyncClient) -> None:
    response = await client.post(
        "/menu/items",
        json={
            "name": "Unauthorized item",
            "menu_group": "Основное меню",
            "section": "Кофе",
            "description": "",
            "ingredients": "",
            "image_url": "",
            "tags": [],
            "variants": [{"portion": "200 мл", "price": 1, "label": ""}],
            "is_available": True,
            "is_featured": False,
            "position": 0,
        },
    )
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_login_me_logout_and_role_boundaries(client: AsyncClient) -> None:
    login_response = await client.post(
        "/auth/login",
        json={
            "username": "owner",
            "password": "owner12345",
        },
    )
    assert login_response.status_code == 200
    access_token = login_response.json()["access_token"]
    headers = {"Authorization": f"Bearer {access_token}"}

    me_response = await client.get("/auth/me", headers=headers)
    assert me_response.status_code == 200
    assert me_response.json()["role"] == "super_admin"
    assert me_response.json()["username"] == "owner"

    create_user_response = await client.post(
        "/auth/users",
        headers=headers,
        json={
            "username": "cashier_mike",
            "full_name": "Mike Romanov",
            "role": "staff_admin",
            "password": "cashier123",
            "is_active": True,
        },
    )
    assert create_user_response.status_code == 201
    created_user = create_user_response.json()
    assert created_user["username"] == "cashier_mike"

    disable_user_response = await client.patch(
        f"/auth/users/{created_user['id']}",
        headers=headers,
        json={
            "is_active": False,
        },
    )
    assert disable_user_response.status_code == 200
    assert disable_user_response.json()["is_active"] is False

    logout_response = await client.post("/auth/logout", headers=headers)
    assert logout_response.status_code == 204

    expired_me_response = await client.get("/auth/me", headers=headers)
    assert expired_me_response.status_code == 401

    staff_headers = await login_and_get_headers(
        client,
        username="barista_anna",
        password="barista123",
    )
    staff_users_response = await client.get("/auth/users", headers=staff_headers)
    assert staff_users_response.status_code == 403
