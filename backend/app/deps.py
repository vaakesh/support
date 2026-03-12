from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession

from app.service import UnitOfWork

from .database import async_session_maker


async def get_session() -> AsyncGenerator[AsyncSession]:
    async with async_session_maker() as session:
        yield session


def get_uow() -> UnitOfWork:
    return UnitOfWork(async_session_maker)
