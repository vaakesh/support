from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession

from app.service import UnitOfWork

from app.database import get_async_session_maker


async def get_session() -> AsyncGenerator[AsyncSession]:
    async with get_async_session_maker()() as session:
        yield session


def get_uow() -> UnitOfWork:
    return UnitOfWork(get_async_session_maker())
