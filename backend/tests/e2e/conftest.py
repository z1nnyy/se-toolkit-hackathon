import os

import httpx
import pytest


@pytest.fixture(scope="session")
def api_base_url() -> str:
    value = os.environ.get("CAVA_API_BASE_URL", "")
    if not value:
        pytest.skip("CAVA_API_BASE_URL is not set")
    return value.rstrip("/")


@pytest.fixture(scope="session")
def client(api_base_url: str) -> httpx.Client:
    return httpx.Client(base_url=api_base_url)
