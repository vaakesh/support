import logging

import pytest
import pytest_asyncio
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from sqlalchemy.pool import NullPool
from app.config import get_settings
from app.main import create_app
from app.database import get_async_session_maker
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy import delete
from app.users.models import User

logger = logging.getLogger(__name__)


@pytest.fixture(scope="session")
def settings():
    return get_settings()


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


@pytest_asyncio.fixture(scope="session")
async def client(app: FastAPI):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="https://test") as ac:
        yield ac


async def clear_db(session_maker, settings):
    logger.info(f"clearing database {settings.db_name}...")
    assert settings.db_name == "support_test", (
        f"refusting to clear non-test DB: {settings.db_name}"
    )
    async with session_maker() as session:
        await session.execute(delete(User))
        await session.commit()


@pytest_asyncio.fixture(autouse=True)
async def cleanup_db(session_maker, settings):
    await clear_db(session_maker, settings)
    yield
    await clear_db(session_maker, settings)
