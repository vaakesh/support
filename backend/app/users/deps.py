from fastapi import Depends
from redis.asyncio import Redis

from app.deps import get_redis, get_uow
from app.service import UnitOfWork
from app.users.service import UserService


def get_user_service(
        uow: UnitOfWork = Depends(get_uow),
        redis: Redis = Depends(get_redis),
) -> UserService:
    return UserService(uow, redis)
