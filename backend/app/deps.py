from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession

from .database import async_session_maker


async def get_session() -> AsyncGenerator[AsyncSession]:
    async with async_session_maker() as session:
        yield session
