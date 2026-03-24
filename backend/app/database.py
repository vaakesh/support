from functools import lru_cache

from redis.asyncio import ConnectionPool
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from app.config import get_settings

@lru_cache
def get_engine() -> AsyncEngine:
    settings = get_settings()
    return create_async_engine(
        settings.database_url(),
        echo=False,
    )

@lru_cache
def get_async_session_maker() -> async_sessionmaker[AsyncSession]:
    return async_sessionmaker(
        bind=get_engine(),
        expire_on_commit=False,
    )

@lru_cache
def get_redis_pool() -> ConnectionPool:
    settings = get_settings()
    return ConnectionPool.from_url(
        settings.redis_url(),
        decode_responses=True,
        max_connections=20,
    )

class Base(DeclarativeBase):
    __abstract__ = True
