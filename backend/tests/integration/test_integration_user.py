







import logging
from fastapi import FastAPI, status
from httpx import AsyncClient
import pytest
import pytest_asyncio

from app.service import UnitOfWork
from tests.helpers import make_user_payload


@pytest.mark.asyncio
async def test_create_user_success(client: AsyncClient) -> None:
    payload = make_user_payload()
    response = await client.post("/users/", json=payload)

    assert response.status_code == status.HTTP_201_CREATED
    data = response.json()
    assert data["username"] == payload["username"]
    assert data["email"] == payload["email"]
    assert "password" not in data

@pytest.mark.asyncio
async def test_create_user_duplicate_returns_conflict(client: AsyncClient) -> None:
    payload = make_user_payload()
    await client.post("/users/", json=payload)
    response = await client.post("/users/", json=payload)

    assert response.status_code == status.HTTP_409_CONFLICT

@pytest.mark.asyncio
async def test_create_user_invalid_email_returns_422(client: AsyncClient) -> None:
    payload = make_user_payload(email="not-an-email")
    response = await client.post("/users/", json=payload)

    assert response.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT

@pytest.mark.asyncio
async def test_update_user(auth_cookies_client: AsyncClient, existing_user: dict) -> None:
    update_payload = make_user_payload(username="updated_username", email="updated@example.com")
    response = await auth_cookies_client.patch(f"/users/{existing_user['uuid']}", json=update_payload)

    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["username"] == update_payload["username"]
    assert data["email"] == update_payload["email"]

    get_response = await auth_cookies_client.get(f"/users/{existing_user['uuid']}")
    assert get_response.json()["username"] == update_payload["username"]

@pytest.mark.asyncio
async def test_update_user_unauthenticated_returns_401(
    client: AsyncClient, existing_user: dict
) -> None:
    response = await client.patch(
        f"/users/{existing_user['uuid']}", json=make_user_payload()
    )
    assert response.status_code == status.HTTP_401_UNAUTHORIZED

@pytest.mark.asyncio
async def test_update_foreign_user_returns_403(
    auth_cookies_client: AsyncClient,
) -> None:
    other_user = make_user_payload()
    create_response = await auth_cookies_client.post("/users/", json=other_user)
    data = create_response.json()

    response = await auth_cookies_client.patch(
        f"/users/{data['uuid']}", json=make_user_payload()
    )
    assert response.status_code == status.HTTP_403_FORBIDDEN

@pytest.mark.asyncio
async def test_delete_user(auth_bearer_client, existing_user):
    response = await auth_bearer_client.delete(f"/users/{existing_user['uuid']}")
    assert response.status_code == status.HTTP_204_NO_CONTENT

    get_response = await auth_bearer_client.get(f"/users/{existing_user['uuid']}")
    assert get_response.status_code == status.HTTP_404_NOT_FOUND

@pytest.mark.asyncio
async def test_delete_other_user(
    auth_bearer_client: AsyncClient,
) -> None:
    other_user = make_user_payload()
    create_response = await auth_bearer_client.post("/users/", json=other_user)
    other_uuid = create_response.json()["uuid"]

    response = await auth_bearer_client.delete(f"/users/{other_uuid}")
    assert response.status_code == status.HTTP_403_FORBIDDEN