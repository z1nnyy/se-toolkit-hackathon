from __future__ import annotations

from cava_backend.models.menu_item import MenuPoster


MENU_POSTERS = [
    MenuPoster(
        id="main-menu",
        title="Основное меню",
        description="Главный постер с напитками, завтраками, супами, салатами и фаст-фудом.",
        asset_path="/menu-assets/menu-posters/main-menu.png",
        groups=["Основное меню"],
    ),
    MenuPoster(
        id="pizza-menu",
        title="Пицца",
        description="Пицца, закрытая пицца и большие пиццы 40 см.",
        asset_path="/menu-assets/menu-posters/pizza-menu.png",
        groups=["Пицца"],
    ),
    MenuPoster(
        id="student-menu",
        title="Студенческое меню",
        description="Отдельный студенческий набор блюд и напитков.",
        asset_path="/menu-assets/menu-posters/student-menu.png",
        groups=["Студенческое меню"],
    ),
    MenuPoster(
        id="spring-menu",
        title="Весеннее меню",
        description="Сезонные напитки, паста, салаты и десерты.",
        asset_path="/menu-assets/menu-posters/spring-menu.png",
        groups=["Весеннее меню"],
    ),
]


def get_menu_posters() -> list[MenuPoster]:
    return MENU_POSTERS


def get_poster_asset_paths_for_group(menu_group: str) -> list[str]:
    normalized_group = menu_group.casefold()
    return [
        poster.asset_path
        for poster in MENU_POSTERS
        if any(group.casefold() == normalized_group for group in poster.groups)
    ]
