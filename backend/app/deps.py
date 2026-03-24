from collections.abc import AsyncGenerator
import logging

from fastapi import Depends
from redis.asyncio import Redis, ConnectionPool
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.service import UnitOfWork

from app.database import get_async_session_maker, get_redis_pool

logger = logging.getLogger(__name__)

async def get_session(
        session_maker = Depends(get_async_session_maker),
) -> AsyncGenerator[AsyncSession]:
    async with session_maker() as session:
        yield session

async def get_redis(
        pool: ConnectionPool = Depends(get_redis_pool),
) -> AsyncGenerator[Redis]:
    async with Redis(connection_pool=pool) as redis:
        yield redis

def get_uow(
        session_maker: async_sessionmaker[AsyncSession] = Depends(get_async_session_maker),
) -> UnitOfWork:
    return UnitOfWork(session_maker)
