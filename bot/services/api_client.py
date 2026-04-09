from __future__ import annotations

from dataclasses import dataclass
from typing import Any
from urllib.parse import urlencode

import httpx


class BackendServiceError(Exception):
    """Raised when the menu API cannot be reached or returns an error."""


@dataclass(slots=True)
class MenuApiClient:
    base_url: str
    timeout_seconds: float = 10.0

    def _request(
        self,
        method: str,
        path: str,
        *,
        params: dict[str, str] | None = None,
    ) -> Any:
        url = f"{self.base_url.rstrip('/')}{path}"

        try:
            with httpx.Client(timeout=self.timeout_seconds) as client:
                response = client.request(method, url, params=params)
                response.raise_for_status()
                return response.json()
        except httpx.HTTPStatusError as exc:
            status = exc.response.status_code
            raise BackendServiceError(
                f"Сервис меню временно недоступен: HTTP {status}."
            ) from exc
        except httpx.ConnectError as exc:
            raise BackendServiceError(
                f"Не удалось подключиться к backend по адресу {self.base_url}."
            ) from exc
        except httpx.TimeoutException as exc:
            raise BackendServiceError("Backend меню не ответил вовремя.") from exc
        except httpx.RequestError as exc:
            raise BackendServiceError(f"Ошибка запроса к меню: {exc}") from exc

    def resolve_asset_url(self, asset_path: str) -> str:
        return f"{self.base_url.rstrip('/')}{asset_path}"

    def build_menu_render_url(
        self,
        *,
        language: str,
        menu_group: str | None = None,
        section: str | None = None,
        available_only: bool = False,
        unavailable_only: bool = False,
        width: int = 1280,
        page: int = 1,
        single_page: bool = False,
    ) -> str:
        params: dict[str, str] = {
            "language": language,
            "width": str(width),
            "page": str(page),
        }
        if menu_group:
            params["menu_group"] = menu_group
        if section:
            params["section"] = section
        if available_only:
            params["available_only"] = "true"
        if unavailable_only:
            params["unavailable_only"] = "true"
        if single_page:
            params["single_page"] = "true"
        query = urlencode(params)
        return f"{self.base_url.rstrip('/')}/menu/render?{query}"

    def get_render_manifest(
        self,
        *,
        language: str,
        menu_group: str | None = None,
        section: str | None = None,
        available_only: bool = False,
        unavailable_only: bool = False,
        width: int = 1280,
        single_page: bool = False,
    ) -> dict[str, Any]:
        params: dict[str, str] = {
            "language": language,
            "width": str(width),
        }
        if menu_group:
            params["menu_group"] = menu_group
        if section:
            params["section"] = section
        if available_only:
            params["available_only"] = "true"
        if unavailable_only:
            params["unavailable_only"] = "true"
        if single_page:
            params["single_page"] = "true"
        return self._request("GET", "/menu/render-manifest", params=params)

    def get_health(self) -> dict[str, Any]:
        return self._request("GET", "/health")

    def get_items(
        self,
        *,
        menu_group: str | None = None,
        section: str | None = None,
        available_only: bool = False,
        unavailable_only: bool = False,
        search: str | None = None,
    ) -> list[dict[str, Any]]:
        params: dict[str, str] = {}
        if menu_group:
            params["menu_group"] = menu_group
        if section:
            params["section"] = section
        if available_only:
            params["available_only"] = "true"
        if unavailable_only:
            params["unavailable_only"] = "true"
        if search:
            params["search"] = search
        return self._request("GET", "/menu/items", params=params)

    def get_groups(self) -> list[str]:
        return self._request("GET", "/menu/groups")

    def get_catalog(self) -> list[dict[str, Any]]:
        return self._request("GET", "/menu/catalog")

    def get_sections(self, *, menu_group: str | None = None) -> list[str]:
        params = {"menu_group": menu_group} if menu_group else None
        return self._request("GET", "/menu/sections", params=params)

    def get_posters(self) -> list[dict[str, Any]]:
        return self._request("GET", "/menu/posters")

    def get_summary(self) -> dict[str, Any]:
        return self._request("GET", "/menu/summary")
