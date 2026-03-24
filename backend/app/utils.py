from datetime import UTC, datetime

from fastapi import Depends, Request
from redis.asyncio import Redis

from app.errors import TooManyRequestsError
from app.deps import get_redis
import secrets


def utcnow() -> datetime:
    return datetime.now(UTC)

def format_duration(duration: float) -> str:
    if duration > 1.0:
        color = "\x1b[31m"
    elif duration > 0.3:
        color = "\x1b[33m"
    else:
        color = "\x1b[32m"
    reset = "\x1b[0m"
    return f"{color}{duration:.3f}s{reset}"

class RateLimit:
    def __init__(self, limit: int, window_seconds: int):
        self.limit = limit
        self.window_seconds = window_seconds

    async def __call__(
        self,
        request: Request, 
        redis: Redis = Depends(get_redis),
    ):
        keys = [request.client.host]
        for key in keys:
            redis_key = f"rate_limit:{key}"
            count = await redis.incr(redis_key, amount = 1)
            print(redis_key, count)
            if count == 1:
                await redis.expire(redis_key, self.window_seconds)

            if count > self.limit:
                raise TooManyRequestsError()