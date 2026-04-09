import httpx


def test_healthcheck_returns_200(client: httpx.Client) -> None:
    response = client.get("/health")
    assert response.status_code == 200


def test_public_menu_items_endpoint_returns_a_list(client: httpx.Client) -> None:
    response = client.get("/menu/items")
    assert response.status_code == 200
    assert isinstance(response.json(), list)


def test_public_menu_posters_endpoint_returns_a_list(client: httpx.Client) -> None:
    response = client.get("/menu/posters")
    assert response.status_code == 200
    assert isinstance(response.json(), list)


def test_public_menu_render_endpoint_returns_png(client: httpx.Client) -> None:
    response = client.get("/menu/render", params={"language": "ru", "width": 1200})
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("image/png")


def test_public_menu_render_manifest_returns_pages(client: httpx.Client) -> None:
    response = client.get("/menu/render-manifest", params={"language": "ru", "width": 1200})
    assert response.status_code == 200
    payload = response.json()
    assert isinstance(payload["total_pages"], int)
    assert payload["total_pages"] >= 1
    assert isinstance(payload["pages"], list)
