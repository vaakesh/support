







from httpx import AsyncClient
import pytest
from fastapi import status


@pytest.mark.asyncio
async def test_logout_success(auth_cookies_client: AsyncClient) -> None:
    response = await auth_cookies_client.post("/auth/logout")

    assert response.status_code == status.HTTP_200_OK

    assert response.cookies.get("access_token") is None
    assert response.cookies.get("refresh_token") is None

@pytest.mark.asyncio
async def test_logout_without_refresh_token_returns_200(client: AsyncClient) -> None:

    response = await client.post("/auth/logout")

    assert response.status_code == status.HTTP_200_OK

@pytest.mark.asyncio
async def test_logout_invalidates_refresh_token(
    client: AsyncClient, existing_user: dict
) -> None:
    # Логинимся, получаем куки
    login_response = await client.post("/auth/login", data={
        "username": existing_user["username"],
        "password": existing_user["password"],
    })
    assert login_response.status_code == status.HTTP_200_OK

    # Логаутимся
    logout_response = await client.post("/auth/logout")
    assert logout_response.status_code == status.HTTP_200_OK

    # Попытка рефреша с отозванным токеном должна провалиться
    refresh_response = await client.post("/auth/refresh")
    assert refresh_response.status_code == status.HTTP_401_UNAUTHORIZED

@pytest.mark.asyncio
async def test_refresh_success(auth_cookies_client: AsyncClient) -> None:
    response = await auth_cookies_client.post("/auth/refresh")

    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert "access_token" in data
    assert "refresh_token" in data
    # Новые токены выставлены в куки
    assert "access_token" in response.cookies
    assert "refresh_token" in response.cookies

@pytest.mark.asyncio
async def test_refresh_returns_new_tokens(auth_cookies_client: AsyncClient) -> None:
    # Первый рефреш
    first = await auth_cookies_client.post("/auth/refresh")
    assert first.status_code == status.HTTP_200_OK
    first_access = first.json()["access_token"]

    # Второй рефреш — токены должны быть новыми
    second = await auth_cookies_client.post("/auth/refresh")
    assert second.status_code == status.HTTP_200_OK
    second_access = second.json()["access_token"]

    assert first_access != second_access


@pytest.mark.asyncio
async def test_refresh_token_rotation(auth_cookies_client: AsyncClient) -> None:
    old_refresh = auth_cookies_client.cookies.get("refresh_token")
    first = await auth_cookies_client.post("/auth/refresh")
    assert first.status_code == status.HTTP_200_OK

    auth_cookies_client.cookies.set("refresh_token", old_refresh, path="/")

    second = await auth_cookies_client.post("/auth/refresh")
    assert second.status_code == status.HTTP_401_UNAUTHORIZED


@pytest.mark.asyncio
async def test_refresh_without_cookie_returns_401(client: AsyncClient) -> None:
    response = await client.post("/auth/refresh")

    assert response.status_code == status.HTTP_401_UNAUTHORIZED


@pytest.mark.asyncio
async def test_refresh_with_invalid_token_returns_401(client: AsyncClient) -> None:
    client.cookies.set("refresh_token", "invalid.token.value", path="/auth/refresh")
    response = await client.post("/auth/refresh")

    assert response.status_code == status.HTTP_401_UNAUTHORIZED

@pytest.mark.asyncio
async def test_get_sessions_returns_current_session(
    auth_cookies_client: AsyncClient,
) -> None:
    response = await auth_cookies_client.get("/auth/sessions")

    assert response.status_code == status.HTTP_200_OK
    sessions = response.json()
    assert isinstance(sessions, list)
    assert len(sessions) >= 1

@pytest.mark.asyncio
async def test_get_sessions_unauthenticated_returns_401(
    client: AsyncClient,
) -> None:
    response = await client.get("/auth/sessions")

    assert response.status_code == status.HTTP_401_UNAUTHORIZED

@pytest.mark.asyncio
async def test_get_sessions_multiple_logins(
    client: AsyncClient, existing_user: dict
) -> None:
    # Два логина с одного аккаунта = две сессии
    for _ in range(2):
        await client.post("/auth/login", data={
            "username": existing_user["username"],
            "password": existing_user["password"],
        })

    response = await client.get("/auth/sessions")
    assert response.status_code == status.HTTP_200_OK
    sessions = response.json()
    assert len(sessions) >= 2
