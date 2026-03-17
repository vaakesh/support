from collections.abc import AsyncGenerator
import logging

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.service import UnitOfWork

from app.database import get_async_session_maker
logger = logging.getLogger(__name__)

async def get_session(
        session_maker = Depends(get_async_session_maker),
) -> AsyncGenerator[AsyncSession]:
    async with session_maker() as session:
        yield session


def get_uow(
        session_maker = Depends(get_async_session_maker),
) -> UnitOfWork:
    return UnitOfWork(session_maker)
