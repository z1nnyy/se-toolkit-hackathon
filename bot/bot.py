from __future__ import annotations

import argparse
import asyncio
import shlex
from dataclasses import dataclass
from typing import Any

from aiogram import Bot, Dispatcher, F
from aiogram.exceptions import TelegramBadRequest
from aiogram.filters import CommandStart
from aiogram.types import (
    CallbackQuery,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    InputMediaPhoto,
    Message,
    ReplyKeyboardRemove,
    URLInputFile,
)

from config import ROOT_DIR, load_settings
from handlers.commands import (
    BotReply,
    MAIN_GROUP,
    PIZZA_GROUP,
    SPRING_GROUP,
    STUDENT_GROUP,
    build_handlers,
    dispatch_free_text,
    normalize_language,
)
from services.api_client import BackendServiceError, MenuApiClient
from services.language_store import UserLanguageStore


LANGUAGE_STORAGE_PATH = ROOT_DIR / "data" / "bot-language-preferences.json"
LANGUAGE_STORE = UserLanguageStore(LANGUAGE_STORAGE_PATH)
ACTIVE_MENU_MESSAGES: dict[int, int] = {}
ACTIVE_MENU_STATES: dict[int, str] = {}
DEFAULT_RENDER_WIDTH = 2200
SOLD_OUT_VIEW_KEY = "soldout"
CORE_MENU_ORDER = [
    MAIN_GROUP,
    PIZZA_GROUP,
    STUDENT_GROUP,
    SPRING_GROUP,
]
GROUP_TRANSLATIONS = {
    MAIN_GROUP: "Main Menu",
    PIZZA_GROUP: "Pizza",
    STUDENT_GROUP: "Student Menu",
    SPRING_GROUP: "Spring Menu",
}
SOLD_OUT_LABELS = {
    "ru": "Нет в наличии",
    "en": "Sold Out",
}
LANGUAGE_LABELS = {
    "ru": "Русский",
    "en": "English",
}


@dataclass(slots=True)
class MenuScreen:
    view_key: str
    language: str
    image_url: str
    caption: str
    active_catalog: list[dict[str, Any]]


def validate_configured_bot_token(token: str | None) -> str | None:
    if not token:
        return "BOT_TOKEN is missing in .env.bot."

    normalized = token.strip()
    if normalized.startswith("<") and normalized.endswith(">"):
        return (
            "BOT_TOKEN in .env.bot is still the placeholder value. "
            "Replace <telegram-bot-token> with the real token from @BotFather."
        )

    if ":" not in normalized:
        return "BOT_TOKEN has an invalid format. It should look like 123456789:ABCDEF..."

    prefix, suffix = normalized.split(":", 1)
    if not prefix.isdigit() or not suffix:
        return "BOT_TOKEN has an invalid format. The part before ':' must be numeric."

    if any(character.isspace() for character in normalized):
        return "BOT_TOKEN must not contain spaces or line breaks."

    return None


def parse_language_choice(text: str) -> str | None:
    normalized = text.strip().lower()
    aliases = {
        "ru": "ru",
        "русский": "ru",
        "russian": "ru",
        "en": "en",
        "english": "en",
    }
    return aliases.get(normalized)


def resolve_user_language(user_id: int, preferred_language_code: str | None = None) -> str:
    default_language = normalize_language(preferred_language_code)
    return LANGUAGE_STORE.get(user_id, default=default_language)


def _build_client() -> MenuApiClient:
    settings = load_settings()
    return MenuApiClient(
        base_url=settings.menu_api_base_url,
        timeout_seconds=settings.menu_request_timeout,
    )


def _set_current_state(chat_id: int, *, view_key: str, message_id: int) -> None:
    ACTIVE_MENU_STATES[chat_id] = view_key
    ACTIVE_MENU_MESSAGES[chat_id] = message_id


def _safe_localized_group_name(name: str, language: str) -> str:
    if language == "en":
        return GROUP_TRANSLATIONS.get(name, name)
    return name


def _active_catalog(client: MenuApiClient) -> list[dict[str, Any]]:
    catalog = client.get_catalog()
    active_catalog = [menu for menu in catalog if not menu.get("deleted_at")]
    order_map = {name: index for index, name in enumerate(CORE_MENU_ORDER)}
    return sorted(
        active_catalog,
        key=lambda menu: (
            order_map.get(str(menu.get("name", "")), len(order_map)),
            -int(menu.get("id", 0)),
        ),
    )


def _default_view_key(active_catalog: list[dict[str, Any]]) -> str:
    if not active_catalog:
        return SOLD_OUT_VIEW_KEY
    return f"menu:{int(active_catalog[0]['id'])}"


def _render_width_for_view(
    view_key: str,
    active_catalog: list[dict[str, Any]],
) -> int:
    if view_key == SOLD_OUT_VIEW_KEY:
        return 2200

    menu = _resolve_menu_from_view_key(active_catalog, view_key)
    if menu is None:
        return DEFAULT_RENDER_WIDTH

    item_count = int(menu.get("active_items", 0))
    if item_count >= 56:
        return 5000
    if item_count >= 28:
        return 2400
    if item_count >= 16:
        return 2200
    return 2000


def _resolve_menu_from_view_key(
    active_catalog: list[dict[str, Any]],
    view_key: str,
) -> dict[str, Any] | None:
    if not view_key.startswith("menu:"):
        return None
    try:
        menu_id = int(view_key.split(":", 1)[1])
    except ValueError:
        return None
    return next((menu for menu in active_catalog if int(menu["id"]) == menu_id), None)


def _view_callback_data(view_key: str) -> str:
    if view_key == SOLD_OUT_VIEW_KEY:
        return "view:soldout"
    return f"view:{view_key}"


def _language_callback_data(language: str) -> str:
    return f"lang:{language}"


def _chunk_buttons(
    buttons: list[InlineKeyboardButton],
    *,
    size: int,
) -> list[list[InlineKeyboardButton]]:
    return [buttons[index : index + size] for index in range(0, len(buttons), size)]


def _build_caption(title: str, language: str) -> str:
    if language == "en":
        return f"{title}\nTap the buttons below to switch menus and language."
    return f"{title}\nПереключайте меню и язык кнопками ниже."


def _build_inline_keyboard(screen: MenuScreen) -> InlineKeyboardMarkup:
    menu_buttons = [
        InlineKeyboardButton(
            text=(
                f"• {_safe_localized_group_name(str(menu['name']), screen.language)}"
                if screen.view_key == f"menu:{int(menu['id'])}"
                else _safe_localized_group_name(str(menu["name"]), screen.language)
            ),
            callback_data=_view_callback_data(f"menu:{int(menu['id'])}"),
        )
        for menu in screen.active_catalog
    ]

    rows = _chunk_buttons(menu_buttons, size=3)
    sold_out_label = SOLD_OUT_LABELS[screen.language]
    rows.append(
        [
            InlineKeyboardButton(
                text=f"• {sold_out_label}" if screen.view_key == SOLD_OUT_VIEW_KEY else sold_out_label,
                callback_data=_view_callback_data(SOLD_OUT_VIEW_KEY),
            )
        ]
    )
    rows.append(
        [
            InlineKeyboardButton(
                text=f"• {LANGUAGE_LABELS['ru']}" if screen.language == "ru" else LANGUAGE_LABELS["ru"],
                callback_data=_language_callback_data("ru"),
            ),
            InlineKeyboardButton(
                text=f"• {LANGUAGE_LABELS['en']}" if screen.language == "en" else LANGUAGE_LABELS["en"],
                callback_data=_language_callback_data("en"),
            ),
        ]
    )
    return InlineKeyboardMarkup(inline_keyboard=rows)


def _build_screen(
    client: MenuApiClient,
    *,
    language: str,
    view_key: str,
) -> MenuScreen:
    active_catalog = _active_catalog(client)
    normalized_view_key = view_key
    if normalized_view_key != SOLD_OUT_VIEW_KEY and _resolve_menu_from_view_key(active_catalog, normalized_view_key) is None:
        normalized_view_key = _default_view_key(active_catalog)

    if normalized_view_key == SOLD_OUT_VIEW_KEY:
        title = SOLD_OUT_LABELS[language]
        render_width = _render_width_for_view(normalized_view_key, active_catalog)
        image_url = client.build_menu_render_url(
            language=language,
            unavailable_only=True,
            width=render_width,
            single_page=True,
        )
    else:
        menu = _resolve_menu_from_view_key(active_catalog, normalized_view_key)
        if menu is None:
            normalized_view_key = SOLD_OUT_VIEW_KEY
            title = SOLD_OUT_LABELS[language]
            image_url = client.build_menu_render_url(
                language=language,
                unavailable_only=True,
                width=DEFAULT_RENDER_WIDTH,
                single_page=True,
            )
        else:
            title = _safe_localized_group_name(str(menu["name"]), language)
            render_width = _render_width_for_view(normalized_view_key, active_catalog)
            image_url = client.build_menu_render_url(
                language=language,
                menu_group=str(menu["name"]),
                width=render_width,
                single_page=True,
            )

    return MenuScreen(
        view_key=normalized_view_key,
        language=language,
        image_url=image_url,
        caption=_build_caption(title, language),
        active_catalog=active_catalog,
    )


async def _safe_delete_message(bot: Bot, chat_id: int, message_id: int) -> None:
    try:
        await bot.delete_message(chat_id=chat_id, message_id=message_id)
    except TelegramBadRequest:
        return


async def _safe_delete_user_message(message: Message) -> None:
    try:
        await message.delete()
    except TelegramBadRequest:
        return


async def _send_new_menu_message(
    bot: Bot,
    *,
    chat_id: int,
    screen: MenuScreen,
) -> int:
    placeholder = await bot.send_message(
        chat_id=chat_id,
        text="\u2060",
        reply_markup=ReplyKeyboardRemove(),
    )
    try:
        await bot.edit_message_media(
            chat_id=chat_id,
            message_id=placeholder.message_id,
            media=InputMediaPhoto(
                media=URLInputFile(screen.image_url),
                caption=screen.caption,
            ),
            reply_markup=_build_inline_keyboard(screen),
        )
        _set_current_state(
            chat_id,
            view_key=screen.view_key,
            message_id=placeholder.message_id,
        )
        return placeholder.message_id
    except TelegramBadRequest:
        await _safe_delete_message(bot, chat_id, placeholder.message_id)
        sent_message = await bot.send_photo(
            chat_id=chat_id,
            photo=URLInputFile(screen.image_url),
            caption=screen.caption,
            reply_markup=_build_inline_keyboard(screen),
        )
        _set_current_state(
            chat_id,
            view_key=screen.view_key,
            message_id=sent_message.message_id,
        )
        return sent_message.message_id


async def _edit_existing_menu_message(
    bot: Bot,
    *,
    chat_id: int,
    message_id: int,
    screen: MenuScreen,
) -> bool:
    try:
        await bot.edit_message_media(
            chat_id=chat_id,
            message_id=message_id,
            media=InputMediaPhoto(
                media=URLInputFile(screen.image_url),
                caption=screen.caption,
            ),
            reply_markup=_build_inline_keyboard(screen),
        )
    except TelegramBadRequest as exc:
        if "message is not modified" in str(exc).lower():
            await bot.edit_message_reply_markup(
                chat_id=chat_id,
                message_id=message_id,
                reply_markup=_build_inline_keyboard(screen),
            )
        else:
            return False

    _set_current_state(
        chat_id,
        view_key=screen.view_key,
        message_id=message_id,
    )
    return True


async def _present_menu(
    bot: Bot,
    *,
    chat_id: int,
    user_id: int,
    preferred_language_code: str | None,
    view_key: str,
    target_message_id: int | None = None,
    replace_active: bool = False,
    force_new_message: bool = False,
) -> None:
    language = resolve_user_language(user_id, preferred_language_code)
    screen = _build_screen(
        _build_client(),
        language=language,
        view_key=view_key,
    )

    active_message_id = ACTIVE_MENU_MESSAGES.get(chat_id)
    if force_new_message:
        if active_message_id is not None:
            await _safe_delete_message(bot, chat_id, active_message_id)
        ACTIVE_MENU_MESSAGES.pop(chat_id, None)
        ACTIVE_MENU_STATES.pop(chat_id, None)
        await _send_new_menu_message(bot, chat_id=chat_id, screen=screen)
        return

    if replace_active and active_message_id is not None and active_message_id != target_message_id:
        await _safe_delete_message(bot, chat_id, active_message_id)
        active_message_id = None

    if target_message_id is not None:
        edited = await _edit_existing_menu_message(
            bot,
            chat_id=chat_id,
            message_id=target_message_id,
            screen=screen,
        )
        if edited:
            return

    if active_message_id is not None:
        edited = await _edit_existing_menu_message(
            bot,
            chat_id=chat_id,
            message_id=active_message_id,
            screen=screen,
        )
        if edited:
            return

    await _send_new_menu_message(bot, chat_id=chat_id, screen=screen)


def _resolve_view_key_for_menu_name(client: MenuApiClient, menu_name: str) -> str | None:
    for menu in _active_catalog(client):
        if str(menu["name"]) == menu_name:
            return f"menu:{int(menu['id'])}"
    return None


def _parse_message_action(text: str) -> tuple[str, str] | None:
    normalized_text = text.strip()
    lowered = normalized_text.lower()

    if lowered in {"/start", "/menu", "/menuimage"}:
        return ("default", "")
    if lowered == "/mainmenu":
        return ("menu_name", MAIN_GROUP)
    if lowered == "/pizza":
        return ("menu_name", PIZZA_GROUP)
    if lowered == "/studentmenu":
        return ("menu_name", STUDENT_GROUP)
    if lowered == "/springmenu":
        return ("menu_name", SPRING_GROUP)
    if lowered == "/available":
        return ("soldout", "")

    if lowered.startswith("/language"):
        parts = shlex.split(normalized_text)
        if len(parts) > 1:
            language = parse_language_choice(parts[1])
            if language is not None:
                return ("language", language)

    language = parse_language_choice(normalized_text)
    if language is not None:
        return ("language", language)

    return None


def dispatch_response(
    text: str,
    *,
    user_id: int = 0,
    preferred_language_code: str | None = None,
) -> BotReply:
    current_language = resolve_user_language(user_id, preferred_language_code)

    if text.startswith("/language"):
        parts = shlex.split(text)
        if len(parts) == 1:
            return BotReply(text="Choose a language with /language ru or /language en.")

        selected_language = parse_language_choice(parts[1])
        if selected_language is None:
            return BotReply(text="Choose a language with /language ru or /language en.")

        LANGUAGE_STORE.set(user_id, selected_language)
        return BotReply(
            text=(
                "Language switched to English."
                if selected_language == "en"
                else "Язык переключен на русский."
            )
        )

    selected_language = parse_language_choice(text)
    if selected_language is not None:
        LANGUAGE_STORE.set(user_id, selected_language)
        return BotReply(
            text=(
                "Language switched to English."
                if selected_language == "en"
                else "Язык переключен на русский."
            )
        )

    if text.startswith("/"):
        parts = shlex.split(text)
        if not parts:
            return BotReply(text="Введите команду целиком.")

        handlers = build_handlers(current_language)
        handler = handlers.get(parts[0])
        if handler is None:
            if current_language == "en":
                return BotReply(text=f"Unknown command: {parts[0]}. Use /start.")
            return BotReply(text=f"Неизвестная команда: {parts[0]}. Используйте /start.")
        return handler(parts[1:])

    return dispatch_free_text(text, current_language)


def run_test_mode(command_text: str, language: str | None) -> int:
    if language:
        LANGUAGE_STORE.set(0, normalize_language(language))
    print(dispatch_response(command_text, user_id=0).text)
    return 0


async def run_telegram_mode() -> int:
    settings = load_settings()
    token_error = validate_configured_bot_token(settings.bot_token)
    if token_error is not None:
        print(token_error)
        return 1

    bot = Bot(settings.bot_token.strip())
    dispatcher = Dispatcher()

    @dispatcher.message(CommandStart())
    async def handle_start_message(message: Message) -> None:
        user_id = message.from_user.id if message.from_user else 0
        chat_id = message.chat.id
        detected_language = message.from_user.language_code if message.from_user else None
        client = _build_client()
        try:
            await _present_menu(
                bot,
                chat_id=chat_id,
                user_id=user_id,
                preferred_language_code=detected_language,
                view_key=_default_view_key(_active_catalog(client)),
                force_new_message=True,
            )
        except BackendServiceError as exc:
            await bot.send_message(chat_id=chat_id, text=str(exc))
        await _safe_delete_user_message(message)

    @dispatcher.callback_query(F.data.startswith("view:"))
    async def handle_view_callback(callback: CallbackQuery) -> None:
        if callback.message is None:
            await callback.answer()
            return

        view_key = callback.data.removeprefix("view:")
        user_id = callback.from_user.id
        chat_id = callback.message.chat.id
        detected_language = callback.from_user.language_code
        try:
            await _present_menu(
                bot,
                chat_id=chat_id,
                user_id=user_id,
                preferred_language_code=detected_language,
                view_key=view_key,
                target_message_id=callback.message.message_id,
                replace_active=True,
            )
        except BackendServiceError as exc:
            await callback.answer(str(exc), show_alert=True)
            return
        await callback.answer()

    @dispatcher.callback_query(F.data.startswith("lang:"))
    async def handle_language_callback(callback: CallbackQuery) -> None:
        if callback.message is None:
            await callback.answer()
            return

        selected_language = callback.data.removeprefix("lang:")
        user_id = callback.from_user.id
        chat_id = callback.message.chat.id
        LANGUAGE_STORE.set(user_id, selected_language)
        current_view = ACTIVE_MENU_STATES.get(chat_id)
        if current_view is None:
            current_view = _default_view_key(_active_catalog(_build_client()))
        try:
            await _present_menu(
                bot,
                chat_id=chat_id,
                user_id=user_id,
                preferred_language_code=selected_language,
                view_key=current_view,
                target_message_id=callback.message.message_id,
                replace_active=True,
            )
        except BackendServiceError as exc:
            await callback.answer(str(exc), show_alert=True)
            return
        await callback.answer()

    @dispatcher.message()
    async def handle_text_message(message: Message) -> None:
        text = (message.text or "").strip()
        if not text:
            return

        action = _parse_message_action(text)
        user_id = message.from_user.id if message.from_user else 0
        chat_id = message.chat.id
        detected_language = message.from_user.language_code if message.from_user else None
        await _safe_delete_user_message(message)

        client = _build_client()
        default_view = _default_view_key(_active_catalog(client))

        if action is None:
            if chat_id not in ACTIVE_MENU_MESSAGES:
                try:
                    await _present_menu(
                        bot,
                        chat_id=chat_id,
                        user_id=user_id,
                        preferred_language_code=detected_language,
                        view_key=default_view,
                    )
                except BackendServiceError:
                    return
            return

        action_type, payload = action
        if action_type == "language":
            LANGUAGE_STORE.set(user_id, payload)
            try:
                await _present_menu(
                    bot,
                    chat_id=chat_id,
                    user_id=user_id,
                    preferred_language_code=payload,
                    view_key=ACTIVE_MENU_STATES.get(chat_id, default_view),
                )
            except BackendServiceError:
                return
            return

        if action_type == "menu_name":
            target_view = _resolve_view_key_for_menu_name(client, payload) or default_view
        elif action_type == "soldout":
            target_view = SOLD_OUT_VIEW_KEY
        else:
            target_view = default_view

        try:
            await _present_menu(
                bot,
                chat_id=chat_id,
                user_id=user_id,
                preferred_language_code=detected_language,
                view_key=target_view,
            )
        except BackendServiceError:
            return

    await dispatcher.start_polling(bot)
    return 0


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--test", metavar="COMMAND")
    parser.add_argument("--lang", choices=["ru", "en"])
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if args.test is not None:
        return run_test_mode(args.test, args.lang)

    return asyncio.run(run_telegram_mode())


if __name__ == "__main__":
    raise SystemExit(main())
