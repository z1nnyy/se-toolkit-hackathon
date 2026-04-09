from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime, timezone
from io import BytesIO
from pathlib import Path
from typing import Literal
from zoneinfo import ZoneInfo

from PIL import Image, ImageDraw, ImageFont

from cava_backend.models.menu_item import MenuEntryRecord, MenuRenderManifest, MenuRenderPage


Language = Literal["ru", "en"]

MOSCOW_TIMEZONE = ZoneInfo("Europe/Moscow")
GROUP_ORDER = [
    "Основное меню",
    "Пицца",
    "Студенческое меню",
    "Весеннее меню",
]
GROUP_TRANSLATIONS = {
    "Основное меню": "Main Menu",
    "Пицца": "Pizza",
    "Студенческое меню": "Student Menu",
    "Весеннее меню": "Spring Menu",
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
BACKGROUND_COLOR = "#ece1cc"
PAPER_COLOR = "#fbf6ea"
PANEL_COLOR = "#fffaf0"
TEXT_COLOR = "#4b3a2b"
MUTED_TEXT_COLOR = "#786655"
DIVIDER_COLOR = "#d6c2ac"
PRICE_COLOR = "#8a4d35"
FEATURED_COLOR = "#ad8552"
SOLD_OUT_COLOR = "#b56363"
HEADER_COLOR = "#8e7262"
TITLE_FONT_CANDIDATES = [
    "/System/Library/Fonts/Supplemental/Baskerville.ttc",
    "/System/Library/Fonts/Supplemental/Times New Roman Bold.ttf",
    "/System/Library/Fonts/Supplemental/Georgia Bold.ttf",
    "/System/Library/Fonts/Supplemental/Didot.ttc",
    "/Library/Fonts/Georgia Bold.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSerif-Bold.ttf",
]
BODY_FONT_CANDIDATES = [
    "/System/Library/Fonts/Supplemental/Arial Unicode.ttf",
    "/System/Library/Fonts/Supplemental/Arial.ttf",
    "/System/Library/Fonts/Supplemental/Helvetica.ttc",
    "/Library/Fonts/Arial Unicode.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    "/usr/share/fonts/truetype/liberation2/LiberationSans-Regular.ttf",
]
BODY_BOLD_FONT_CANDIDATES = [
    "/System/Library/Fonts/Supplemental/Arial Bold.ttf",
    "/System/Library/Fonts/Supplemental/Helvetica.ttc",
    "/Library/Fonts/Arial Bold.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
    "/usr/share/fonts/truetype/liberation2/LiberationSans-Bold.ttf",
]
GROUP_ACCENTS = {
    "Основное меню": ("#b37b80", "#edd8d7"),
    "Пицца": ("#8da486", "#dde8da"),
    "Студенческое меню": ("#c7a05d", "#f0e1bc"),
    "Весеннее меню": ("#83a79d", "#d5e5df"),
}


@dataclass(slots=True)
class RenderFonts:
    title: ImageFont.ImageFont
    subtitle: ImageFont.ImageFont
    page_badge: ImageFont.ImageFont
    section_title: ImageFont.ImageFont
    section_tag: ImageFont.ImageFont
    item_name: ImageFont.ImageFont
    item_meta: ImageFont.ImageFont
    item_note: ImageFont.ImageFont
    footer: ImageFont.ImageFont


@dataclass(slots=True)
class RenderConfig:
    width: int
    height: int
    outer_padding: int
    panel_padding: int
    header_height: int
    footer_height: int
    card_padding: int
    card_gap: int
    column_gap: int
    columns: int
    column_width: int
    section_header_height: int
    item_gap: int
    note_spacing: int
    body_spacing: int
    shadow_offset: int


@dataclass(slots=True)
class ItemLayout:
    name_lines: list[str]
    variant_lines: list[str]
    note_lines: list[str]
    is_available: bool
    is_featured: bool
    height: int


@dataclass(slots=True)
class SectionCardLayout:
    group_name: str
    section_name: str
    title_lines: list[str]
    accent_color: str
    accent_soft_color: str
    items: list[ItemLayout]
    continued: bool
    header_height: int
    height: int


@dataclass(slots=True)
class RenderPageLayout:
    title: str
    subtitle: str
    cards_by_column: list[list[SectionCardLayout]]


@dataclass(slots=True)
class SinglePageLayoutCandidate:
    config: RenderConfig
    fonts: RenderFonts
    cards: list[SectionCardLayout]
    cards_by_column: list[list[SectionCardLayout]]
    column_heights: list[int]
    score: float


def _load_font(
    size: int,
    *,
    bold: bool = False,
    title: bool = False,
) -> ImageFont.ImageFont:
    if title:
        candidates = TITLE_FONT_CANDIDATES
    elif bold:
        candidates = BODY_BOLD_FONT_CANDIDATES
    else:
        candidates = BODY_FONT_CANDIDATES

    for candidate in candidates:
        path = Path(candidate)
        if not path.exists():
            continue
        try:
            return ImageFont.truetype(str(path), size=size)
        except OSError:
            continue
    return ImageFont.load_default()


def _build_fonts(width: int, *, density_scale: float = 1.0) -> RenderFonts:
    def scaled(value: int) -> int:
        return max(12, int(round(value * density_scale)))

    return RenderFonts(
        title=_load_font(scaled(max(46, width // 22)), title=True),
        subtitle=_load_font(scaled(max(20, width // 52))),
        page_badge=_load_font(scaled(max(18, width // 62)), bold=True),
        section_title=_load_font(scaled(max(24, width // 46)), bold=True),
        section_tag=_load_font(scaled(max(16, width // 74)), bold=True),
        item_name=_load_font(scaled(max(20, width // 60)), bold=True),
        item_meta=_load_font(scaled(max(17, width // 72)), bold=True),
        item_note=_load_font(scaled(max(15, width // 82))),
        footer=_load_font(scaled(max(15, width // 86))),
    )


def _build_config(
    width: int,
    *,
    columns_override: int | None = None,
    density_scale: float = 1.0,
    height_ratio: float = 1.38,
) -> RenderConfig:
    canvas_width = max(900, min(width, 5000))
    canvas_height = int(canvas_width * height_ratio)

    def scaled(base: int, floor: int) -> int:
        return max(floor, int(round(base * density_scale)))

    outer_padding = scaled(canvas_width // 30, 28)
    panel_padding = scaled(canvas_width // 32, 24)
    header_height = scaled(canvas_width // 5, 180)
    footer_height = scaled(canvas_width // 24, 58)
    card_padding = scaled(canvas_width // 52, 18)
    card_gap = scaled(canvas_width // 48, 16)
    column_gap = scaled(canvas_width // 40, 18)
    if columns_override is not None:
        columns = columns_override
    elif canvas_width >= 4200:
        columns = 8
    elif canvas_width >= 3000:
        columns = 6
    elif canvas_width >= 2400:
        columns = 5
    elif canvas_width >= 1800:
        columns = 4
    elif canvas_width >= 1400:
        columns = 3
    elif canvas_width >= 1100:
        columns = 2
    else:
        columns = 1
    column_width = (
        canvas_width
        - (outer_padding * 2)
        - (panel_padding * 2)
        - (column_gap * (columns - 1))
    ) // columns
    return RenderConfig(
        width=canvas_width,
        height=canvas_height,
        outer_padding=outer_padding,
        panel_padding=panel_padding,
        header_height=header_height,
        footer_height=footer_height,
        card_padding=card_padding,
        card_gap=card_gap,
        column_gap=column_gap,
        columns=columns,
        column_width=column_width,
        section_header_height=scaled(canvas_width // 28, 46),
        item_gap=scaled(canvas_width // 70, 12),
        note_spacing=scaled(5, 4),
        body_spacing=scaled(6, 4),
        shadow_offset=scaled(canvas_width // 180, 4),
    )


def _localize_group(value: str, language: Language) -> str:
    if language == "ru":
        return value
    return GROUP_TRANSLATIONS.get(value, value)


def _localize_section(value: str, language: Language) -> str:
    if language == "ru":
        return value
    return SECTION_TRANSLATIONS.get(value, value)


def _localize_text(primary: str, secondary: str, language: Language) -> str:
    if language == "en" and secondary.strip():
        return secondary.strip()
    return primary.strip()


def _localize_variant(value: str, language: Language) -> str:
    if language == "ru":
        return value
    return (
        value.replace(" мл", " ml")
        .replace(" гр", " g")
        .replace(" см", " cm")
        .replace("шт", "pcs")
    )


def _format_price(value: float) -> str:
    return f"{value:.0f} RUB"


def _to_moscow_datetime(value: datetime | None) -> datetime | None:
    if value is None:
        return None
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return value.astimezone(MOSCOW_TIMEZONE)


def _format_timestamp(value: datetime | None, language: Language) -> str:
    localized = _to_moscow_datetime(value)
    if localized is None:
        return ""
    timestamp = localized.strftime("%d.%m.%y %H:%M")
    if language == "en":
        return f"Updated {timestamp} MSK"
    return f"Обновлено {timestamp} МСК"


def _measure_text(draw: ImageDraw.ImageDraw, text: str, font: ImageFont.ImageFont) -> int:
    if not text:
        return 0
    left, _, right, _ = draw.textbbox((0, 0), text, font=font)
    return right - left


def _text_box(
    draw: ImageDraw.ImageDraw,
    text: str,
    font: ImageFont.ImageFont,
) -> tuple[int, int, int, int]:
    return draw.textbbox((0, 0), text, font=font)


def _line_height(draw: ImageDraw.ImageDraw, font: ImageFont.ImageFont) -> int:
    _, top, _, bottom = draw.textbbox((0, 0), "Ag", font=font)
    return bottom - top


def _split_long_token(
    draw: ImageDraw.ImageDraw,
    token: str,
    font: ImageFont.ImageFont,
    max_width: int,
) -> list[str]:
    if _measure_text(draw, token, font) <= max_width:
        return [token]

    chunks: list[str] = []
    current = ""
    for character in token:
        candidate = f"{current}{character}"
        if current and _measure_text(draw, candidate, font) > max_width:
            chunks.append(current)
            current = character
            continue
        current = candidate

    if current:
        chunks.append(current)

    return chunks or [token]


def _wrap_text(
    draw: ImageDraw.ImageDraw,
    text: str,
    font: ImageFont.ImageFont,
    max_width: int,
    *,
    max_lines: int | None = None,
) -> list[str]:
    if not text.strip():
        return []

    words: list[str] = []
    for token in text.split():
        words.extend(_split_long_token(draw, token, font, max_width))
    lines: list[str] = []
    current_line = words[0]

    for word in words[1:]:
        candidate = f"{current_line} {word}"
        if _measure_text(draw, candidate, font) <= max_width:
            current_line = candidate
            continue

        lines.append(current_line)
        current_line = word

    lines.append(current_line)

    if max_lines is not None and len(lines) > max_lines:
        lines = lines[:max_lines]
        while lines and _measure_text(draw, f"{lines[-1]}...", font) > max_width:
            parts = lines[-1].split()
            if len(parts) <= 1:
                lines[-1] = lines[-1][:-1]
                continue
            lines[-1] = " ".join(parts[:-1])
        if lines:
            lines[-1] = f"{lines[-1]}..."

    return lines


def _multiline_height(
    draw: ImageDraw.ImageDraw,
    lines: list[str],
    font: ImageFont.ImageFont,
    *,
    spacing: int,
) -> int:
    if not lines:
        return 0
    return (_line_height(draw, font) * len(lines)) + (spacing * (len(lines) - 1))


def _badge_height(
    draw: ImageDraw.ImageDraw,
    font: ImageFont.ImageFont,
    *,
    vertical_padding: int = 6,
) -> int:
    return _line_height(draw, font) + (vertical_padding * 2)


def _badge_block_height(
    draw: ImageDraw.ImageDraw,
    font: ImageFont.ImageFont,
    *,
    vertical_padding: int = 6,
    gap_after: int = 6,
) -> int:
    return _badge_height(draw, font, vertical_padding=vertical_padding) + gap_after


def _section_title_top(
    draw: ImageDraw.ImageDraw,
    fonts: RenderFonts,
) -> int:
    return 16 + _badge_height(draw, fonts.section_tag, vertical_padding=6) + 12


def _section_header_height(
    draw: ImageDraw.ImageDraw,
    title_lines: list[str],
    config: RenderConfig,
    fonts: RenderFonts,
) -> int:
    section_title_height = _multiline_height(
        draw,
        title_lines,
        fonts.section_title,
        spacing=config.body_spacing,
    )
    return max(
        config.section_header_height,
        _section_title_top(draw, fonts) + section_title_height + 18,
    )


def _draw_text_centered(
    draw: ImageDraw.ImageDraw,
    text: str,
    font: ImageFont.ImageFont,
    *,
    x: int,
    y: int,
    width: int,
    height: int,
    fill: str,
) -> None:
    left, top, right, bottom = _text_box(draw, text, font)
    text_width = right - left
    text_height = bottom - top
    text_x = x + ((width - text_width) / 2) - left
    text_y = y + ((height - text_height) / 2) - top
    draw.text((text_x, text_y), text, font=font, fill=fill)


def _draw_badge(
    draw: ImageDraw.ImageDraw,
    *,
    text: str,
    font: ImageFont.ImageFont,
    x: int,
    y: int,
    max_width: int,
    fill: str,
    text_fill: str,
    horizontal_padding: int = 14,
    vertical_padding: int = 6,
    radius: int = 14,
) -> tuple[int, int]:
    width = min(
        max_width,
        _measure_text(draw, text, font) + (horizontal_padding * 2),
    )
    height = _badge_height(draw, font, vertical_padding=vertical_padding)
    draw.rounded_rectangle(
        (x, y, x + width, y + height),
        radius=radius,
        fill=fill,
    )
    _draw_text_centered(
        draw,
        text,
        font,
        x=x,
        y=y,
        width=width,
        height=height,
        fill=text_fill,
    )
    return width, height


def _build_title(
    *,
    menu_group: str | None,
    section: str | None,
    available_only: bool,
    unavailable_only: bool,
    language: Language,
) -> str:
    if section:
        section_name = _localize_section(section, language)
        return f"Cava · {section_name}" if language == "en" else f"Cava · {section_name}"

    if menu_group:
        return _localize_group(menu_group, language)

    if available_only:
        return "Available Now" if language == "en" else "Сейчас в наличии"

    if unavailable_only:
        return "Sold Out" if language == "en" else "Нет в наличии"

    return "Cava Menu" if language == "en" else "Меню Cava"


def _build_subtitle(
    items: list[MenuEntryRecord],
    *,
    language: Language,
) -> str:
    updated = max((item.updated_at for item in items), default=None)
    summary = f"{len(items)} items" if language == "en" else f"{len(items)} позиций"
    timestamp = _format_timestamp(updated, language)
    return f"{summary} • {timestamp}" if timestamp else summary


def _ordered_sections(
    items: list[MenuEntryRecord],
) -> list[tuple[str, str, list[MenuEntryRecord]]]:
    grouped: dict[str, dict[str, list[MenuEntryRecord]]] = defaultdict(lambda: defaultdict(list))
    for item in items:
        grouped[item.menu_group][item.section].append(item)

    ordered_groups = sorted(
        grouped,
        key=lambda value: (GROUP_ORDER.index(value) if value in GROUP_ORDER else len(GROUP_ORDER), value),
    )
    sections: list[tuple[str, str, list[MenuEntryRecord]]] = []
    for group_name in ordered_groups:
        for section_name, section_items in grouped[group_name].items():
            sections.append((group_name, section_name, section_items))
    return sections


def _group_accent(group_name: str) -> tuple[str, str]:
    return GROUP_ACCENTS.get(group_name, ("#9d7a61", "#e7dccf"))


def _build_variant_lines(
    item: MenuEntryRecord,
    draw: ImageDraw.ImageDraw,
    config: RenderConfig,
    fonts: RenderFonts,
    language: Language,
) -> list[str]:
    fragments: list[str] = []
    for variant in item.variants:
        label = str(variant.get("label", "")).strip()
        portion = _localize_variant(str(variant.get("portion", "")).strip(), language)
        price = _format_price(float(variant.get("price", 0)))
        prefix = f"{label} " if label else ""
        fragments.append(f"{prefix}{portion} · {price}")
    return _wrap_text(
        draw,
        "  •  ".join(fragments),
        fonts.item_meta,
        config.column_width - (config.card_padding * 2),
        max_lines=3,
    )


def _build_note_lines(
    item: MenuEntryRecord,
    draw: ImageDraw.ImageDraw,
    config: RenderConfig,
    fonts: RenderFonts,
    language: Language,
) -> list[str]:
    description = _localize_text(item.description, item.description_en, language)
    ingredients = _localize_text(item.ingredients, item.ingredients_en, language)
    if description and ingredients:
        note = f"{description} • {ingredients}"
    else:
        note = description or ingredients
    return _wrap_text(
        draw,
        note,
        fonts.item_note,
        config.column_width - (config.card_padding * 2),
        max_lines=2,
    )


def _pack_cards_into_columns(
    cards: list[SectionCardLayout],
    *,
    columns: int,
    card_gap: int,
) -> tuple[list[list[SectionCardLayout]], list[int]]:
    cards_by_column: list[list[SectionCardLayout]] = [[] for _ in range(columns)]
    column_heights = [0 for _ in range(columns)]
    for card in cards:
        target_column = min(range(columns), key=lambda index: column_heights[index])
        cards_by_column[target_column].append(card)
        column_heights[target_column] += card.height
        if len(cards_by_column[target_column]) > 1:
            column_heights[target_column] += card_gap
    return cards_by_column, column_heights


def _build_item_layout(
    item: MenuEntryRecord,
    draw: ImageDraw.ImageDraw,
    config: RenderConfig,
    fonts: RenderFonts,
    language: Language,
) -> ItemLayout:
    sold_out_suffix = "" if item.is_available else (
        " [sold out]" if language == "en" else " [нет в наличии]"
    )
    name_text = f"{_localize_text(item.name, item.name_en, language)}{sold_out_suffix}"
    name_lines = _wrap_text(
        draw,
        name_text,
        fonts.item_name,
        config.column_width - (config.card_padding * 2),
        max_lines=3,
    )
    variant_lines = _build_variant_lines(item, draw, config, fonts, language)
    note_lines = _build_note_lines(item, draw, config, fonts, language)
    badge_height = 0
    if item.is_featured:
        badge_height += _badge_block_height(draw, fonts.section_tag)
    if not item.is_available:
        badge_height += _badge_block_height(draw, fonts.section_tag)
    inner_gaps_height = 16
    height = (
        badge_height
        + inner_gaps_height
        + _multiline_height(draw, name_lines, fonts.item_name, spacing=config.body_spacing)
        + _multiline_height(draw, variant_lines, fonts.item_meta, spacing=config.note_spacing)
        + _multiline_height(draw, note_lines, fonts.item_note, spacing=config.note_spacing)
        + config.item_gap
    )
    return ItemLayout(
        name_lines=name_lines,
        variant_lines=variant_lines,
        note_lines=note_lines,
        is_available=item.is_available,
        is_featured=item.is_featured,
        height=height,
    )


def _density_scale_for_items(item_count: int) -> float:
    if item_count >= 60:
        return 0.58
    if item_count >= 40:
        return 0.66
    if item_count >= 24:
        return 0.82
    if item_count <= 8:
        return 1.1
    if item_count <= 14:
        return 1.04
    return 1.0


def _build_card_height(
    draw: ImageDraw.ImageDraw,
    title_lines: list[str],
    card_items: list[ItemLayout],
    config: RenderConfig,
    fonts: RenderFonts,
) -> int:
    header_height = _section_header_height(draw, title_lines, config, fonts)
    total_items_height = sum(item.height for item in card_items)
    return (
        config.card_padding
        + header_height
        + total_items_height
        + config.card_padding
        - 6
    )


def _build_section_title_lines(
    section_name: str,
    *,
    continued: bool,
    draw: ImageDraw.ImageDraw,
    config: RenderConfig,
    fonts: RenderFonts,
    language: Language,
) -> list[str]:
    title = _localize_section(section_name, language)
    if continued:
        title = (
            f"{title} · continued"
            if language == "en"
            else f"{title} · продолжение"
        )
    return _wrap_text(
        draw,
        title,
        fonts.section_title,
        config.column_width - (config.card_padding * 2),
        max_lines=3,
    )


def _build_cards(
    items: list[MenuEntryRecord],
    *,
    language: Language,
    config: RenderConfig,
    fonts: RenderFonts,
    draw: ImageDraw.ImageDraw,
    single_page: bool = False,
) -> list[SectionCardLayout]:
    if single_page:
        if len(items) >= 48:
            max_card_height = max(640, int(config.width * 0.28))
        elif len(items) >= 24:
            max_card_height = max(720, int(config.width * 0.34))
        elif len(items) >= 12:
            max_card_height = max(820, int(config.width * 0.42))
        else:
            max_card_height = 10**9
    else:
        max_card_height = config.height - (
            config.outer_padding * 2
            + config.panel_padding * 2
            + config.header_height
            + config.footer_height
            + config.card_gap
        )
    cards: list[SectionCardLayout] = []

    for group_name, section_name, section_items in _ordered_sections(items):
        accent_color, accent_soft_color = _group_accent(group_name)
        item_layouts = [
            _build_item_layout(item, draw, config, fonts, language)
            for item in section_items
        ]

        current_chunk: list[ItemLayout] = []
        current_chunk_continued = False
        for item_layout in item_layouts:
            candidate = [*current_chunk, item_layout]
            candidate_title_lines = _build_section_title_lines(
                section_name,
                continued=current_chunk_continued,
                draw=draw,
                config=config,
                fonts=fonts,
                language=language,
            )
            candidate_height = _build_card_height(
                draw,
                candidate_title_lines,
                candidate,
                config,
                fonts,
            )
            if current_chunk and candidate_height > max_card_height:
                title_lines = _build_section_title_lines(
                    section_name,
                    continued=current_chunk_continued,
                    draw=draw,
                    config=config,
                    fonts=fonts,
                    language=language,
                )
                height = _build_card_height(draw, title_lines, current_chunk, config, fonts)
                cards.append(
                    SectionCardLayout(
                        group_name=group_name,
                        section_name=section_name,
                        title_lines=title_lines,
                        accent_color=accent_color,
                        accent_soft_color=accent_soft_color,
                        items=current_chunk,
                        continued=current_chunk_continued,
                        header_height=_section_header_height(draw, title_lines, config, fonts),
                        height=height,
                    )
                )
                current_chunk = [item_layout]
                current_chunk_continued = True
            else:
                current_chunk = candidate

        if current_chunk:
            title_lines = _build_section_title_lines(
                section_name,
                continued=current_chunk_continued,
                draw=draw,
                config=config,
                fonts=fonts,
                language=language,
            )
            height = _build_card_height(draw, title_lines, current_chunk, config, fonts)
            cards.append(
                SectionCardLayout(
                    group_name=group_name,
                    section_name=section_name,
                    title_lines=title_lines,
                    accent_color=accent_color,
                    accent_soft_color=accent_soft_color,
                    items=current_chunk,
                    continued=current_chunk_continued,
                    header_height=_section_header_height(draw, title_lines, config, fonts),
                    height=height,
                )
            )

    return cards


def _build_pages(
    items: list[MenuEntryRecord],
    *,
    language: Language,
    menu_group: str | None,
    section: str | None,
    available_only: bool,
    unavailable_only: bool,
    width: int,
    single_page: bool = False,
) -> tuple[RenderConfig, RenderFonts, list[RenderPageLayout]]:
    title = _build_title(
        menu_group=menu_group,
        section=section,
        available_only=available_only,
        unavailable_only=unavailable_only,
        language=language,
    )
    subtitle = _build_subtitle(items, language=language)

    if single_page:
        max_columns = (
            10 if width >= 4800 else
            9 if width >= 4200 else
            8 if width >= 3400 else
            7 if width >= 2800 else
            6 if width >= 2400 else
            5 if width >= 2200 else
            4 if width >= 1600 else
            3 if width >= 1100 else
            2
        )
        min_columns = 3 if len(items) >= 36 and width >= 1600 else 1
        base_scale = _density_scale_for_items(len(items))
        target_aspect = (
            1.6 if len(items) >= 48 else
            1.35 if len(items) >= 28 else
            1.1 if len(items) >= 14 else
            0.9
        )
        best_candidate: SinglePageLayoutCandidate | None = None

        tested_scales = {
            round(max(0.54, min(1.18, base_scale * factor)), 2)
            for factor in (0.94, 1.0, 1.06)
        }
        for columns in range(min_columns, max_columns + 1):
            for density_scale in sorted(tested_scales):
                config = _build_config(
                    width,
                    columns_override=columns,
                    density_scale=density_scale,
                    height_ratio=1.0,
                )
                if config.column_width < 260:
                    continue
                fonts = _build_fonts(config.width, density_scale=density_scale)
                measure_canvas = Image.new("RGB", (config.width, max(config.height, 1200)), PAPER_COLOR)
                measure_draw = ImageDraw.Draw(measure_canvas)
                cards = _build_cards(
                    items,
                    language=language,
                    config=config,
                    fonts=fonts,
                    draw=measure_draw,
                    single_page=True,
                )
                cards_by_column, column_heights = _pack_cards_into_columns(
                    cards,
                    columns=config.columns,
                    card_gap=config.card_gap,
                )
                content_height = max(column_heights, default=0)
                required_height = (
                    (config.outer_padding * 2)
                    + (config.panel_padding * 2)
                    + config.header_height
                    + config.footer_height
                    + content_height
                    + config.card_gap
                )
                aspect = config.width / max(required_height, 1)
                imbalance = (
                    (content_height * config.columns) - sum(column_heights)
                ) / max(content_height * config.columns, 1)
                narrow_penalty = max(0.0, (360 - config.column_width) / 360)
                score = (
                    abs(aspect - target_aspect) * 2.4
                    + imbalance * 2.2
                    + narrow_penalty * 0.8
                )

                candidate_config = RenderConfig(
                    width=config.width,
                    height=required_height,
                    outer_padding=config.outer_padding,
                    panel_padding=config.panel_padding,
                    header_height=config.header_height,
                    footer_height=config.footer_height,
                    card_padding=config.card_padding,
                    card_gap=config.card_gap,
                    column_gap=config.column_gap,
                    columns=config.columns,
                    column_width=config.column_width,
                    section_header_height=config.section_header_height,
                    item_gap=config.item_gap,
                    note_spacing=config.note_spacing,
                    body_spacing=config.body_spacing,
                    shadow_offset=config.shadow_offset,
                )
                candidate = SinglePageLayoutCandidate(
                    config=candidate_config,
                    fonts=fonts,
                    cards=cards,
                    cards_by_column=cards_by_column,
                    column_heights=column_heights,
                    score=score,
                )
                if best_candidate is None or candidate.score < best_candidate.score:
                    best_candidate = candidate

        if best_candidate is None:
            config = _build_config(width, height_ratio=1.0)
            fonts = _build_fonts(config.width)
            pages = [RenderPageLayout(title=title, subtitle=subtitle, cards_by_column=[[]])]
            return config, fonts, pages

        return best_candidate.config, best_candidate.fonts, [
            RenderPageLayout(
                title=title,
                subtitle=subtitle,
                cards_by_column=best_candidate.cards_by_column,
            )
        ]

    config = _build_config(width)
    fonts = _build_fonts(config.width)
    measure_canvas = Image.new("RGB", (config.width, config.height), PAPER_COLOR)
    measure_draw = ImageDraw.Draw(measure_canvas)
    cards = _build_cards(
        items,
        language=language,
        config=config,
        fonts=fonts,
        draw=measure_draw,
        single_page=False,
    )

    if not cards:
        return config, fonts, [RenderPageLayout(title=title, subtitle=subtitle, cards_by_column=[[]])]

    max_column_height = (
        config.height
        - (config.outer_padding * 2)
        - (config.panel_padding * 2)
        - config.header_height
        - config.footer_height
    )

    pages: list[RenderPageLayout] = []
    current_columns: list[list[SectionCardLayout]] = [[] for _ in range(config.columns)]
    current_heights = [0 for _ in range(config.columns)]

    for card in cards:
        target_column = min(range(config.columns), key=lambda index: current_heights[index])
        projected_height = current_heights[target_column] + card.height
        if current_columns[target_column]:
            projected_height += config.card_gap

        if projected_height > max_column_height and any(current_columns):
            pages.append(
                RenderPageLayout(
                    title=title,
                    subtitle=subtitle,
                    cards_by_column=[list(column) for column in current_columns],
                )
            )
            current_columns = [[] for _ in range(config.columns)]
            current_heights = [0 for _ in range(config.columns)]
            target_column = 0

        current_columns[target_column].append(card)
        current_heights[target_column] += card.height
        if len(current_columns[target_column]) > 1:
            current_heights[target_column] += config.card_gap

    if any(current_columns):
        pages.append(
            RenderPageLayout(
                title=title,
                subtitle=subtitle,
                cards_by_column=[list(column) for column in current_columns],
            )
        )

    return config, fonts, pages


def build_menu_render_manifest(
    items: list[MenuEntryRecord],
    *,
    language: Language = "ru",
    menu_group: str | None = None,
    section: str | None = None,
    available_only: bool = False,
    unavailable_only: bool = False,
    width: int = 1280,
    single_page: bool = False,
) -> MenuRenderManifest:
    _, _, pages = _build_pages(
        items,
        language=language,
        menu_group=menu_group,
        section=section,
        available_only=available_only,
        unavailable_only=unavailable_only,
        width=width,
        single_page=single_page,
    )
    return MenuRenderManifest(
        total_pages=len(pages),
        pages=[
            MenuRenderPage(
                page=index + 1,
                title=page.title,
            )
            for index, page in enumerate(pages)
        ],
    )


def _draw_background(draw: ImageDraw.ImageDraw, config: RenderConfig) -> None:
    draw.rounded_rectangle(
        (
            config.outer_padding,
            config.outer_padding,
            config.width - config.outer_padding,
            config.height - config.outer_padding,
        ),
        radius=36,
        fill=PAPER_COLOR,
        outline=DIVIDER_COLOR,
        width=2,
    )
    draw.rounded_rectangle(
        (
            config.outer_padding,
            config.outer_padding,
            config.width - config.outer_padding,
            config.outer_padding + config.header_height,
        ),
        radius=36,
        fill=HEADER_COLOR,
    )
    draw.rectangle(
        (
            config.outer_padding,
            config.outer_padding + config.header_height - 36,
            config.width - config.outer_padding,
            config.outer_padding + config.header_height,
        ),
        fill=HEADER_COLOR,
    )
    accent_y = config.outer_padding + config.header_height - 42
    block_width = max(110, config.width // 9)
    for index, color in enumerate(["#d0b56a", "#b37b80", "#8da486"]):
        start_x = config.width - config.outer_padding - ((index + 1) * (block_width + 18))
        draw.rounded_rectangle(
            (
                start_x,
                accent_y,
                start_x + block_width,
                accent_y + 20,
            ),
            radius=10,
            fill=color,
        )


def _draw_header(
    draw: ImageDraw.ImageDraw,
    page: RenderPageLayout,
    config: RenderConfig,
    fonts: RenderFonts,
    *,
    page_number: int,
    total_pages: int,
    language: Language,
) -> None:
    content_x = config.outer_padding + config.panel_padding
    title_y = config.outer_padding + config.panel_padding
    subtitle_y = title_y + _line_height(draw, fonts.title) + 18

    draw.text((content_x, title_y), page.title, font=fonts.title, fill=PAPER_COLOR)
    draw.text((content_x, subtitle_y), page.subtitle, font=fonts.subtitle, fill="#f0e6db")

    badge_text = f"{page_number}/{total_pages}"
    badge_width = _measure_text(draw, badge_text, fonts.page_badge) + 36
    badge_x = config.width - config.outer_padding - config.panel_padding - badge_width
    badge_y = config.outer_padding + config.panel_padding
    _draw_badge(
        draw,
        text=badge_text,
        font=fonts.page_badge,
        x=badge_x,
        y=badge_y,
        max_width=badge_width,
        fill="#f2ebdf",
        text_fill=HEADER_COLOR,
        horizontal_padding=18,
        vertical_padding=10,
        radius=18,
    )

    footer_text = "Generated from live menu data" if language == "en" else "Собрано из актуальных данных меню"
    draw.text(
        (content_x, config.height - config.outer_padding - config.panel_padding),
        footer_text,
        font=fonts.footer,
        fill=MUTED_TEXT_COLOR,
    )


def _draw_card(
    draw: ImageDraw.ImageDraw,
    card: SectionCardLayout,
    *,
    x: int,
    y: int,
    config: RenderConfig,
    fonts: RenderFonts,
    language: Language,
) -> None:
    shadow = config.shadow_offset
    draw.rounded_rectangle(
        (
            x + shadow,
            y + shadow,
            x + config.column_width + shadow,
            y + card.height + shadow,
        ),
        radius=28,
        fill="#d9cbb7",
    )
    draw.rounded_rectangle(
        (x, y, x + config.column_width, y + card.height),
        radius=28,
        fill=PANEL_COLOR,
        outline=DIVIDER_COLOR,
        width=2,
    )
    draw.rounded_rectangle(
        (x, y, x + config.column_width, y + card.header_height + 18),
        radius=28,
        fill=card.accent_soft_color,
    )
    draw.rectangle(
        (x, y + card.header_height, x + config.column_width, y + card.header_height + 18),
        fill=card.accent_soft_color,
    )
    group_label = _localize_group(card.group_name, language)
    _, group_badge_height = _draw_badge(
        draw,
        text=group_label,
        font=fonts.section_tag,
        x=x + config.card_padding,
        y=y + 16,
        max_width=config.column_width - (config.card_padding * 2),
        fill=card.accent_color,
        text_fill=PANEL_COLOR,
    )

    title_y = y + 16 + group_badge_height + 12
    draw.multiline_text(
        (x + config.card_padding, title_y),
        "\n".join(card.title_lines),
        font=fonts.section_title,
        fill=TEXT_COLOR,
        spacing=config.body_spacing,
    )

    cursor_y = y + card.header_height + config.card_padding - 6
    for index, item in enumerate(card.items):
        if index > 0:
            draw.line(
                (
                    x + config.card_padding,
                    cursor_y - 10,
                    x + config.column_width - config.card_padding,
                    cursor_y - 10,
                ),
                fill=DIVIDER_COLOR,
                width=1,
            )
        if item.is_featured:
            _, featured_badge_height = _draw_badge(
                draw,
                text="TOP",
                font=fonts.section_tag,
                x=x + config.card_padding,
                y=cursor_y,
                max_width=max(72, config.column_width // 4),
                fill="#f3e1b0",
                text_fill=FEATURED_COLOR,
                horizontal_padding=16,
                vertical_padding=6,
                radius=12,
            )
            cursor_y += featured_badge_height + 6
        if not item.is_available:
            sold_out_label = "sold out" if language == "en" else "нет в наличии"
            sold_out_badge_width = min(
                config.column_width - (config.card_padding * 2),
                _measure_text(draw, sold_out_label, fonts.section_tag) + 28,
            )
            _, sold_out_badge_height = _draw_badge(
                draw,
                text=sold_out_label,
                font=fonts.section_tag,
                x=x + config.column_width - config.card_padding - sold_out_badge_width,
                y=cursor_y,
                max_width=sold_out_badge_width,
                fill="#f1d7d7",
                text_fill=SOLD_OUT_COLOR,
                horizontal_padding=14,
                vertical_padding=6,
                radius=12,
            )
            cursor_y += sold_out_badge_height + 6

        draw.multiline_text(
            (x + config.card_padding, cursor_y),
            "\n".join(item.name_lines),
            font=fonts.item_name,
            fill=TEXT_COLOR,
            spacing=config.body_spacing,
        )
        cursor_y += _multiline_height(draw, item.name_lines, fonts.item_name, spacing=config.body_spacing) + 8
        draw.multiline_text(
            (x + config.card_padding, cursor_y),
            "\n".join(item.variant_lines),
            font=fonts.item_meta,
            fill=PRICE_COLOR,
            spacing=config.note_spacing,
        )
        cursor_y += _multiline_height(draw, item.variant_lines, fonts.item_meta, spacing=config.note_spacing) + 8
        if item.note_lines:
            draw.multiline_text(
                (x + config.card_padding, cursor_y),
                "\n".join(item.note_lines),
                font=fonts.item_note,
                fill=MUTED_TEXT_COLOR,
                spacing=config.note_spacing,
            )
            cursor_y += _multiline_height(draw, item.note_lines, fonts.item_note, spacing=config.note_spacing)
        cursor_y += config.item_gap


def render_menu_image(
    items: list[MenuEntryRecord],
    *,
    language: Language = "ru",
    menu_group: str | None = None,
    section: str | None = None,
    available_only: bool = False,
    unavailable_only: bool = False,
    width: int = 1280,
    page: int = 1,
    single_page: bool = False,
) -> bytes:
    config, fonts, pages = _build_pages(
        items,
        language=language,
        menu_group=menu_group,
        section=section,
        available_only=available_only,
        unavailable_only=unavailable_only,
        width=width,
        single_page=single_page,
    )
    page_index = min(max(page, 1), len(pages)) - 1
    selected_page = pages[page_index]

    image = Image.new("RGB", (config.width, config.height), BACKGROUND_COLOR)
    draw = ImageDraw.Draw(image)
    _draw_background(draw, config)
    _draw_header(
        draw,
        selected_page,
        config,
        fonts,
        page_number=page_index + 1,
        total_pages=len(pages),
        language=language,
    )

    start_x = config.outer_padding + config.panel_padding
    start_y = config.outer_padding + config.panel_padding + config.header_height
    for column_index, cards in enumerate(selected_page.cards_by_column):
        x = start_x + (column_index * (config.column_width + config.column_gap))
        y = start_y
        for card in cards:
            _draw_card(
                draw,
                card,
                x=x,
                y=y,
                config=config,
                fonts=fonts,
                language=language,
            )
            y += card.height + config.card_gap

    buffer = BytesIO()
    image.save(buffer, format="PNG", optimize=True)
    return buffer.getvalue()
