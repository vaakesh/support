import logging

import pytest
import pytest_asyncio
from fastapi import FastAPI, status
from httpx import ASGITransport, AsyncClient
from redis.asyncio import Redis
from sqlalchemy.pool import NullPool
from app.config import get_settings
from app.main import create_app
from app.database import get_async_session_maker
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy import text
from tests.helpers import make_user_payload


logger = logging.getLogger(__name__)


@pytest.fixture(scope="session")
def settings():
    settings = get_settings()
    if settings.db_name != "support_test":
        pytest.exit(f"Tests aborted: wrong database configured: got \"{settings.db_name}\", expected \"support_test\"")
    return settings


@pytest_asyncio.fixture(scope="session")
async def engine(settings):
    engine = create_async_engine(
        settings.database_url(),
        poolclass=NullPool,
        echo=False,
    )
    yield engine
    await engine.dispose()


@pytest_asyncio.fixture(scope="session")
async def session_maker(engine):
    return async_sessionmaker(
        bind=engine,
        expire_on_commit=False,
    )


@pytest.fixture(scope="session")
def app(session_maker):
    app = create_app()
    app.dependency_overrides[get_async_session_maker] = lambda: session_maker
    yield app
    app.dependency_overrides.pop(get_async_session_maker, None)


@pytest_asyncio.fixture(scope="function")
async def client(app: FastAPI):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="https://test") as ac:
        yield ac


async def clear_db(session_maker, settings):
    assert settings.db_name == "support_test", (
        f"refusing to clear non-test DB: {settings.db_name}"
    )
    async with session_maker() as session:
        await session.execute(text("TRUNCATE TABLE users RESTART IDENTITY CASCADE"))
        await session.commit()


@pytest_asyncio.fixture(autouse=True, scope="function")
async def cleanup_db(session_maker, settings):
    yield
    await clear_db(session_maker, settings)
    redis = Redis.from_url(settings.redis_url())
    await redis.flushdb()
    await redis.aclose()


@pytest_asyncio.fixture(scope="function")
async def existing_user(client):
    payload = make_user_payload(username="current_user", email="currentuser@example.com")
    response = await client.post("/users/", json=payload)
    assert response.status_code == 201
    data = response.json()
    data["password"] = payload["password"]
    return data

@pytest_asyncio.fixture(scope="function")
async def auth_cookies_client(client, existing_user):
    # application/x-www-form-urlencoded
    response = await client.post("/auth/login", data={
        "username": existing_user["username"],
        "password": "testpassword",
    })
    assert response.status_code == status.HTTP_200_OK
    yield client
    client.cookies.clear()

@pytest_asyncio.fixture(scope="function")
async def auth_bearer_client(client, existing_user):
    response = await client.post("/auth/token", data={
        "username": existing_user["username"],
        "password": "testpassword",
    })
    assert response.status_code == status.HTTP_200_OK
    token = response.json()["access_token"]

    client.headers["Authorization"] = f"Bearer {token}"
    yield client
    client.headers.pop("Authorization", None)