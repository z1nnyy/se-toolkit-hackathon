from __future__ import annotations

import re
from collections import defaultdict
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Literal

from config import load_settings
from handlers.shared.messages import WELCOME_MESSAGES
from services.api_client import BackendServiceError, MenuApiClient


Language = Literal["ru", "en"]

MAIN_GROUP = "Основное меню"
PIZZA_GROUP = "Пицца"
STUDENT_GROUP = "Студенческое меню"
SPRING_GROUP = "Весеннее меню"

GROUP_TRANSLATIONS = {
    MAIN_GROUP: "Main Menu",
    PIZZA_GROUP: "Pizza",
    STUDENT_GROUP: "Student Menu",
    SPRING_GROUP: "Spring Menu",
}

SECTION_TRANSLATIONS = {
    "Кофе": "Coffee",
    "Чай": "Tea",
    "Авторские напитки": "Signature Drinks",
    "Бабл чай": "Bubble Tea",
    "Десерты": "Desserts",
    "Завтраки": "Breakfast",
    "Супы": "Soups",
    "Салаты": "Salads",
    "Вторые блюда": "Main Courses",
    "Фаст-фуд": "Fast Food",
    "Закрытые корейские бургеры": "Closed Korean Burgers",
    "Хот-доги": "Hot Dogs",
    "Пицца": "Pizza",
    "Закрытая пицца": "Closed Pizza",
    "Большая пицца": "Large Pizza",
    "Студенческое меню": "Student Menu",
    "Весеннее меню": "Spring Menu",
}

GENERIC_REPLACEMENTS = [
    ("нет в наличии", "sold out"),
    ("молочная пена", "milk foam"),
    ("томатный соус", "tomato sauce"),
    ("белый соус", "white sauce"),
    ("сырный соус", "cheese sauce"),
    ("чесночный соус", "garlic sauce"),
    ("соус", "sauce"),
    ("классический", "classic"),
    ("черный кофе", "black coffee"),
    ("в фильтр-кофеварке", "in a filter coffee machine"),
    ("кофе", "coffee"),
    ("чай", "tea"),
    ("эспрессо", "espresso"),
    ("латте", "latte"),
    ("айс", "iced"),
    ("раф", "raf"),
    ("капучино", "cappuccino"),
    ("пицца", "pizza"),
    ("сэндвич", "sandwich"),
    ("бургер", "burger"),
    ("салат", "salad"),
    ("паста", "pasta"),
    ("курица", "chicken"),
    ("грибной", "mushroom"),
    ("грибы", "mushrooms"),
    ("сырный", "cheese"),
    ("какао", "cocoa"),
    ("лимонад", "lemonade"),
    ("шоколад", "chocolate"),
    ("молоко", "milk"),
    ("сливки", "cream"),
    ("черный", "black"),
    ("горячий", "hot"),
    ("заваренный", "brewed"),
    ("насыщенный", "rich"),
    ("кофейный", "coffee"),
    ("вкус", "flavor"),
    ("текстурное", "textured"),
    ("и", "and"),
    ("рис", "rice"),
    ("мята", "mint"),
    ("лимон", "lemon"),
    ("манго", "mango"),
    ("вишня", "cherry"),
    ("груша", "pear"),
]

CYRILLIC_TO_LATIN = {
    "а": "a",
    "б": "b",
    "в": "v",
    "г": "g",
    "д": "d",
    "е": "e",
    "ё": "yo",
    "ж": "zh",
    "з": "z",
    "и": "i",
    "й": "y",
    "к": "k",
    "л": "l",
    "м": "m",
    "н": "n",
    "о": "o",
    "п": "p",
    "р": "r",
    "с": "s",
    "т": "t",
    "у": "u",
    "ф": "f",
    "х": "kh",
    "ц": "ts",
    "ч": "ch",
    "ш": "sh",
    "щ": "sch",
    "ъ": "",
    "ы": "y",
    "ь": "",
    "э": "e",
    "ю": "yu",
    "я": "ya",
}

SECTION_ALIASES = {
    "coffee": "Кофе",
    "tea": "Чай",
    "dessert": "Десерты",
    "desserts": "Десерты",
    "breakfast": "Завтраки",
    "breakfasts": "Завтраки",
    "soups": "Супы",
    "soup": "Супы",
    "salad": "Салаты",
    "salads": "Салаты",
    "main course": "Вторые блюда",
    "main courses": "Вторые блюда",
    "fast food": "Фаст-фуд",
    "pizza": "Пицца",
    "closed pizza": "Закрытая пицца",
    "large pizza": "Большая пицца",
    "student menu": "Студенческое меню",
    "spring menu": "Весеннее меню",
}


@dataclass(slots=True)
class BotReply:
    text: str
    image_urls: list[str] = field(default_factory=list)


Handler = Callable[[list[str]], BotReply]


def _build_client() -> MenuApiClient:
    settings = load_settings()
    return MenuApiClient(
        base_url=settings.menu_api_base_url,
        timeout_seconds=settings.menu_request_timeout,
    )


def normalize_language(value: str | None) -> Language:
    if value and value.strip().lower().startswith("en"):
        return "en"
    return "ru"


def _message(language: Language, *, ru: str, en: str) -> str:
    return en if language == "en" else ru


def _localize_group(value: str, language: Language) -> str:
    if language == "ru":
        return value
    return GROUP_TRANSLATIONS.get(value, _translate_generic_to_english(value))


def _localize_section(value: str, language: Language) -> str:
    if language == "ru":
        return value
    return SECTION_TRANSLATIONS.get(value, _translate_generic_to_english(value))


def _match_case(replacement: str, source: str) -> str:
    if not source:
        return replacement
    if source.isupper():
        return replacement.upper()
    if source[0].isupper():
        return replacement[:1].upper() + replacement[1:]
    return replacement


def _transliterate_text(text: str) -> str:
    translated: list[str] = []
    for character in text:
        lower_character = character.lower()
        if lower_character not in CYRILLIC_TO_LATIN:
            translated.append(character)
            continue

        replacement = CYRILLIC_TO_LATIN[lower_character]
        if character.isupper() and replacement:
            replacement = replacement[:1].upper() + replacement[1:]
        translated.append(replacement)
    return "".join(translated)


def _translate_generic_to_english(text: str) -> str:
    if not text.strip():
        return ""

    translated = text
    for source, target in GENERIC_REPLACEMENTS:
        translated = re.sub(
            rf"(?<!\w){re.escape(source)}(?!\w)",
            lambda match: _match_case(target, match.group(0)),
            translated,
            flags=re.IGNORECASE,
        )

    translated = translated.replace(" мл", " ml")
    translated = translated.replace(" гр", " g")
    translated = translated.replace(" см", " cm")
    translated = _transliterate_text(translated)
    return re.sub(r"\s+", " ", translated).strip()


def _localize_text(primary: str, secondary: str, language: Language) -> str:
    if language == "ru":
        return primary.strip()
    if secondary.strip():
        return secondary.strip()
    return _translate_generic_to_english(primary)


def _localize_variant_text(value: str, language: Language) -> str:
    if language == "ru":
        return value
    return _translate_generic_to_english(value)


def _format_price(value: float) -> str:
    return f"{value:.0f} RUB"


def _format_variants(
    variants: list[dict[str, object]],
    *,
    language: Language,
) -> str:
    formatted_variants: list[str] = []
    for variant in variants:
        label = _localize_variant_text(str(variant.get("label", "")).strip(), language)
        portion = _localize_variant_text(str(variant.get("portion", "")).strip(), language)
        price = float(variant.get("price", 0))

        variant_label = f"{label}: " if label else ""
        formatted_variants.append(f"{variant_label}{portion} — {_format_price(price)}")

    return " | ".join(formatted_variants)


def _build_render_urls(
    client: MenuApiClient,
    *,
    language: Language,
    menu_group: str | None = None,
    section: str | None = None,
    available_only: bool = False,
    unavailable_only: bool = False,
    width: int = 1400,
) -> list[str]:
    manifest = client.get_render_manifest(
        language=language,
        menu_group=menu_group,
        section=section,
        available_only=available_only,
        unavailable_only=unavailable_only,
        width=width,
        single_page=True,
    )
    pages = manifest.get("pages", [])
    return [
        client.build_menu_render_url(
            language=language,
            menu_group=menu_group,
            section=section,
            available_only=available_only,
            unavailable_only=unavailable_only,
            width=width,
            page=int(page.get("page", 1)),
            single_page=True,
        )
        for page in pages
    ]


def _normalize_render_width(value: str | None) -> int | None:
    if value is None or not value.isdigit():
        return None

    width = int(value)
    return max(720, min(width, 5000))


def _resolve_group_query(query: str) -> str | None:
    normalized_query = query.strip().lower()
    if normalized_query in {"main", "mainmenu", "main menu", "основное", "основное меню"}:
        return MAIN_GROUP
    if normalized_query in {"pizza", "пицца"}:
        return PIZZA_GROUP
    if normalized_query in {"student", "studentmenu", "student menu", "студенческое", "студенческое меню"}:
        return STUDENT_GROUP
    if normalized_query in {"spring", "springmenu", "spring menu", "весеннее", "весеннее меню"}:
        return SPRING_GROUP
    return None


def _format_grouped_items(
    items: list[dict[str, object]],
    *,
    title: str,
    include_group_headers: bool,
    language: Language,
) -> str:
    if not items:
        return _message(
            language,
            ru="По этому запросу ничего не нашлось.",
            en="Nothing matched this request.",
        )

    grouped_items: dict[str, dict[str, list[dict[str, object]]]] = defaultdict(
        lambda: defaultdict(list)
    )
    for item in items:
        grouped_items[str(item["menu_group"])][str(item["section"])].append(item)

    lines = [title]
    for menu_group, sections in grouped_items.items():
        if include_group_headers:
            lines.append("")
            lines.append(_localize_group(menu_group, language))

        for section, section_items in sections.items():
            lines.append("")
            lines.append(_localize_section(section, language))
            for item in section_items:
                item_name = _localize_text(
                    str(item["name"]),
                    str(item.get("name_en", "")),
                    language,
                )
                sold_out_suffix = _message(
                    language,
                    ru="" if item["is_available"] else " [нет в наличии]",
                    en="" if item["is_available"] else " [sold out]",
                )
                featured_prefix = "⭐ " if item["is_featured"] else ""
                variants_text = _format_variants(list(item["variants"]), language=language)
                lines.append(f"- {featured_prefix}{item_name} — {variants_text}{sold_out_suffix}")

                description = _localize_text(
                    str(item.get("description", "")),
                    str(item.get("description_en", "")),
                    language,
                ).strip()
                if description:
                    lines.append(f"  {description}")

                ingredients = _localize_text(
                    str(item.get("ingredients", "")),
                    str(item.get("ingredients_en", "")),
                    language,
                ).strip()
                if ingredients:
                    lines.append(f"  {ingredients}")

    return "\n".join(lines)


def _safe_reply(callback: Callable[[], BotReply]) -> BotReply:
    try:
        return callback()
    except BackendServiceError as exc:
        return BotReply(text=str(exc))


def _group_menu_reply(
    client: MenuApiClient,
    menu_group: str,
    *,
    language: Language,
) -> BotReply:
    items = client.get_items(menu_group=menu_group)
    return BotReply(
        text=_format_grouped_items(
            items,
            title=f"{_localize_group(menu_group, language)}:",
            include_group_headers=False,
            language=language,
        ),
        image_urls=_build_render_urls(client, menu_group=menu_group, language=language),
    )


def _resolve_section_name(query: str, sections: list[str]) -> str | None:
    normalized_query = query.strip().lower()
    for section in sections:
        if section.lower() == normalized_query:
            return section
        english_name = SECTION_TRANSLATIONS.get(section, _translate_generic_to_english(section))
        if english_name.lower() == normalized_query:
            return section
    return SECTION_ALIASES.get(normalized_query)


def handle_start(_: list[str], language: Language) -> BotReply:
    return BotReply(text=WELCOME_MESSAGES[language])


def handle_help(_: list[str], language: Language) -> BotReply:
    if language == "en":
        return BotReply(
            text="\n".join(
                [
                    "How to use the bot:",
                    "/start - open the interactive menu",
                    "Use the buttons under the menu image to switch menus and language",
                    "Use the language buttons to switch Russian and English",
                    "/health - quick backend check",
                    "/language [ru|en] - switch language manually if needed",
                ]
            )
        )

    return BotReply(
        text="\n".join(
            [
                "Как пользоваться ботом:",
                "/start - открыть интерактивное меню",
                "Дальше переключайте меню и язык кнопками под картинкой",
                "Язык тоже можно менять кнопками",
                "/health - быстрая проверка backend",
                "/language [ru|en] - ручная смена языка, если нужно",
            ]
        )
    )


def handle_health(_: list[str], client: MenuApiClient, language: Language) -> BotReply:
    summary = client.get_summary()
    health = client.get_health()
    return BotReply(
        text=_message(
            language,
            ru=(
                f"Backend {health['status']}. "
                f"Всего позиций: {summary['total_items']}, "
                f"доступно сейчас: {summary['available_items']}."
            ),
            en=(
                f"Backend is {health['status']}. "
                f"Total items: {summary['total_items']}, "
                f"available now: {summary['available_items']}."
            ),
        )
    )


def handle_menu_overview(_: list[str], client: MenuApiClient, language: Language) -> BotReply:
    items = client.get_items()
    groups = client.get_groups()
    grouped_counts: dict[str, int] = {group: 0 for group in groups}
    for item in items:
        grouped_counts[str(item["menu_group"])] += 1

    if language == "en":
        lines = [
            "Current Cava menu:",
            "",
            f"- {GROUP_TRANSLATIONS[MAIN_GROUP]}: {grouped_counts.get(MAIN_GROUP, 0)} items",
            f"- {GROUP_TRANSLATIONS[PIZZA_GROUP]}: {grouped_counts.get(PIZZA_GROUP, 0)} items",
            f"- {GROUP_TRANSLATIONS[STUDENT_GROUP]}: {grouped_counts.get(STUDENT_GROUP, 0)} items",
            f"- {GROUP_TRANSLATIONS[SPRING_GROUP]}: {grouped_counts.get(SPRING_GROUP, 0)} items",
            "",
            "Use /mainmenu, /pizza, /studentmenu, or /springmenu for details.",
        ]
        return BotReply(
            text="\n".join(lines),
            image_urls=_build_render_urls(client, language=language),
        )

    lines = [
        "Текущее меню Cava:",
        "",
        f"- {MAIN_GROUP}: {grouped_counts.get(MAIN_GROUP, 0)} позиций",
        f"- {PIZZA_GROUP}: {grouped_counts.get(PIZZA_GROUP, 0)} позиций",
        f"- {STUDENT_GROUP}: {grouped_counts.get(STUDENT_GROUP, 0)} позиций",
        f"- {SPRING_GROUP}: {grouped_counts.get(SPRING_GROUP, 0)} позиций",
        "",
        "Для деталей используйте /mainmenu, /pizza, /studentmenu или /springmenu.",
    ]
    return BotReply(
        text="\n".join(lines),
        image_urls=_build_render_urls(client, language=language),
    )


def handle_available(_: list[str], client: MenuApiClient, language: Language) -> BotReply:
    items = client.get_items(unavailable_only=True)
    return BotReply(
        text=_format_grouped_items(
            items,
            title=_message(
                language,
                ru="Сейчас нет в наличии:",
                en="Currently sold out:",
            ),
            include_group_headers=True,
            language=language,
        ),
        image_urls=_build_render_urls(client, language=language, unavailable_only=True),
    )


def handle_section(args: list[str], client: MenuApiClient, language: Language) -> BotReply:
    if not args:
        return BotReply(
            text=_message(
                language,
                ru="Использование: /section <раздел>",
                en="Usage: /section <section>",
            )
        )

    requested_section = " ".join(args).strip()
    resolved_section = _resolve_section_name(requested_section, client.get_sections())
    if resolved_section is None:
        sections = ", ".join(_localize_section(section, language) for section in client.get_sections())
        return BotReply(
            text=_message(
                language,
                ru=f"Раздел '{requested_section}' не найден. Доступные разделы: {sections}",
                en=f"Section '{requested_section}' was not found. Available sections: {sections}",
            )
        )

    items = client.get_items(section=resolved_section)
    related_group = str(items[0]["menu_group"]) if items else None
    localized_section = _localize_section(resolved_section, language)
    return BotReply(
        text=_format_grouped_items(
            items,
            title=_message(
                language,
                ru=f"Раздел «{localized_section}»:",
                en=f"Section '{localized_section}':",
            ),
            include_group_headers=False,
            language=language,
        ),
        image_urls=_build_render_urls(
            client,
            menu_group=related_group,
            section=resolved_section,
            language=language,
        ),
    )


def handle_menu_image(args: list[str], client: MenuApiClient, language: Language) -> BotReply:
    width = 1400
    target_group: str | None = None

    for argument in args:
        normalized_width = _normalize_render_width(argument)
        if normalized_width is not None:
            width = normalized_width
            continue

        resolved_group = _resolve_group_query(argument)
        if resolved_group is not None:
            target_group = resolved_group

    localized_target = _localize_group(target_group, language) if target_group else None
    return BotReply(
        text=_message(
            language,
            ru=(
                f"Отправляю меню «{localized_target}» картинкой шириной {width}px."
                if localized_target
                else f"Отправляю актуальное меню Cava картинкой шириной {width}px."
            ),
            en=(
                f"Sending the {localized_target} image at {width}px width."
                if localized_target
                else f"Sending the latest Cava menu as an image at {width}px width."
            ),
        ),
        image_urls=_build_render_urls(
            client,
            language=language,
            menu_group=target_group,
            width=width,
        ),
    )


def route_plain_text(text: str, client: MenuApiClient, language: Language) -> BotReply:
    lowered = text.strip().lower()
    if not lowered:
        return BotReply(
            text=_message(
                language,
                ru="Нажмите /start, чтобы открыть меню Cava.",
                en="Press /start to open the Cava menu.",
            )
        )

    if "pizza" in lowered or "пицц" in lowered:
        return _group_menu_reply(client, PIZZA_GROUP, language=language)
    if "spring" in lowered or "весенн" in lowered:
        return _group_menu_reply(client, SPRING_GROUP, language=language)
    if "student" in lowered or "студен" in lowered:
        return _group_menu_reply(client, STUDENT_GROUP, language=language)
    if "main menu" in lowered or "основ" in lowered:
        return _group_menu_reply(client, MAIN_GROUP, language=language)
    if "available" in lowered or "налич" in lowered:
        return handle_available([], client, language)
    if "poster" in lowered or "image" in lowered or "постер" in lowered or "фото меню" in lowered:
        return handle_menu_image([], client, language)
    if "coffee" in lowered or "кофе" in lowered:
        return handle_section(["Кофе"], client, language)
    if "dessert" in lowered or "десерт" in lowered:
        return handle_section(["Десерты"], client, language)
    if "menu" in lowered or "меню" in lowered:
        return handle_menu_overview([], client, language)

    section_name = _resolve_section_name(lowered, client.get_sections())
    if section_name:
        return handle_section([section_name], client, language)

    return BotReply(
        text=_message(
            language,
            ru=(
                "Нажмите /start, и я открою интерактивное меню с кнопками."
            ),
            en=(
                "Press /start and I will open the interactive menu with buttons."
            ),
        )
    )


def build_handlers(language: Language) -> dict[str, Handler]:
    client = _build_client()
    return {
        "/start": lambda args: handle_start(args, language),
        "/help": lambda args: handle_help(args, language),
        "/health": lambda args: _safe_reply(lambda: handle_health(args, client, language)),
        "/menu": lambda args: _safe_reply(lambda: handle_menu_overview(args, client, language)),
        "/menuimage": lambda args: _safe_reply(lambda: handle_menu_image(args, client, language)),
        "/mainmenu": lambda args: _safe_reply(
            lambda: _group_menu_reply(client, MAIN_GROUP, language=language)
        ),
        "/pizza": lambda args: _safe_reply(
            lambda: _group_menu_reply(client, PIZZA_GROUP, language=language)
        ),
        "/studentmenu": lambda args: _safe_reply(
            lambda: _group_menu_reply(client, STUDENT_GROUP, language=language)
        ),
        "/springmenu": lambda args: _safe_reply(
            lambda: _group_menu_reply(client, SPRING_GROUP, language=language)
        ),
        "/available": lambda args: _safe_reply(lambda: handle_available(args, client, language)),
        "/section": lambda args: _safe_reply(lambda: handle_section(args, client, language)),
        "/posters": lambda args: _safe_reply(lambda: handle_menu_image(args, client, language)),
    }


def dispatch_free_text(text: str, language: Language) -> BotReply:
    return _safe_reply(lambda: route_plain_text(text, _build_client(), language))
