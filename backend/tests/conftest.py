import pytest
import pytest_asyncio
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from app.main import create_app
from app.logging_config import setup_logging


@pytest.fixture(scope="session")
def app() -> FastAPI:
    # setup_logging()
    return create_app()


@pytest_asyncio.fixture(scope="session")
async def client(app):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="https://test") as ac:
        yield ac
