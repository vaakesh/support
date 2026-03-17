







import logging
from fastapi import FastAPI, status
import pytest
import pytest_asyncio

from app.service import UnitOfWork

logger = logging.getLogger(__name__)

@pytest_asyncio.fixture
async def existing_user(client):
    payload = make_user_payload()
    response = await client.post("/users/", json=payload)
    assert response.status_code == 201
    data = response.json()
    return data

@pytest_asyncio.fixture()
async def auth_cookies_client(client, existing_user):
    logger.info("sending request for getting cookies tokens")
    response = await client.post("/auth/login", data={
        "username": existing_user["username"],
        "password": "testpassword",
    })
    assert response.status_code == status.HTTP_200_OK
    print(response.headers.get("set-cookie"))
    print(dict(client.cookies))
    yield client
    client.cookies.clear()


@pytest_asyncio.fixture
async def auth_bearer_client(client, existing_user):
    logger.info("sending request for getting bearer token")
    # application/x-www-form-urlencoded
    response = await client.post("/auth/token", data={
        "username": existing_user["username"],
        "password": "testpassword",
    })
    assert response.status_code == status.HTTP_200_OK
    token = response.json()["access_token"]

    client.headers["Authorization"] = f"Bearer {token}"
    logger.info(f"bearer token got = {token}")
    yield client
    client.headers.pop("Authorization", None)



def make_user_payload(username: str = "testuser", email: str = "test@example.com", password: str = "testpassword"):
    payload = {
        "username": username,
        "email": email,
        "password": password,
    }
    return payload

@pytest.mark.asyncio
async def test_create_user_success_and_duplicate(client):
    payload = {
        "username": "testuser",
        "email": "test@example.com",
        "password": "testpassword",
    }
    response = await client.post("/users/", json=payload)
    assert response.status_code == status.HTTP_201_CREATED
    data = response.json()
    assert data["username"] == payload["username"]
    assert data["email"] == payload["email"]

    response = await client.post("/users/", json=payload)
    assert response.status_code == status.HTTP_409_CONFLICT

@pytest.mark.asyncio
async def test_update_user(auth_cookies_client, existing_user):
    update_payload = make_user_payload(username="updated_username", email="updated@example.com", password="updateddd")
    response = await auth_cookies_client.patch(f"/users/{existing_user["uuid"]}", json=update_payload)
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["username"] == update_payload["username"]
    assert data["email"] == update_payload["email"]

@pytest.mark.asyncio
async def test_delete_user(auth_bearer_client, existing_user):
    response = await auth_bearer_client.delete(f"/users/{existing_user["uuid"]}")
    assert response.status_code == status.HTTP_204_NO_CONTENT
