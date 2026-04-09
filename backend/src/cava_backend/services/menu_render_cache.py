from __future__ import annotations

import hashlib
import json
from pathlib import Path

from cava_backend.settings import settings


MENU_RENDER_CACHE_VERSION = "v3"


def get_menu_render_cache_dir() -> Path:
    cache_dir = Path(settings.menu_render_cache_dir).expanduser().resolve()
    cache_dir.mkdir(parents=True, exist_ok=True)
    return cache_dir


def get_menu_render_cache_path(
    *,
    language: str,
    menu_group: str | None,
    section: str | None,
    available_only: bool,
    unavailable_only: bool = False,
    width: int,
    page: int = 1,
    single_page: bool = False,
) -> Path:
    payload = {
        "version": MENU_RENDER_CACHE_VERSION,
        "language": language,
        "menu_group": menu_group or "",
        "section": section or "",
        "available_only": available_only,
        "unavailable_only": unavailable_only,
        "width": width,
        "page": page,
        "single_page": single_page,
    }
    digest = hashlib.sha1(
        json.dumps(payload, ensure_ascii=False, sort_keys=True).encode("utf-8")
    ).hexdigest()
    return get_menu_render_cache_dir() / f"{digest}.png"


def store_menu_render_cache(
    image_bytes: bytes,
    *,
    language: str,
    menu_group: str | None,
    section: str | None,
    available_only: bool,
    unavailable_only: bool = False,
    width: int,
    page: int = 1,
    single_page: bool = False,
) -> Path:
    target_path = get_menu_render_cache_path(
        language=language,
        menu_group=menu_group,
        section=section,
        available_only=available_only,
        unavailable_only=unavailable_only,
        width=width,
        page=page,
        single_page=single_page,
    )
    temporary_path = target_path.with_suffix(".tmp")
    temporary_path.write_bytes(image_bytes)
    temporary_path.replace(target_path)
    return target_path


def invalidate_menu_render_cache() -> None:
    cache_dir = get_menu_render_cache_dir()
    for cached_file in cache_dir.glob("*"):
        if not cached_file.is_file():
            continue
        cached_file.unlink(missing_ok=True)
