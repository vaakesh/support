from collections.abc import Awaitable, Callable
from contextlib import asynccontextmanager
import logging
import time

from fastapi import FastAPI, Request, Response
from fastapi.responses import HTMLResponse
from redis.asyncio import Redis

import app.models  # noqa: F401 # sqlalchemy models registration
from app.auth.router import router as auth_router
from app.exception_handlers import register_exception_handlers
from app.logging_config import setup_logging
from app.users.router import router as users_router
from app.tickets.router import router as ticket_router
from app.utils import format_duration
from app.database import get_redis_pool
from app.deps import get_redis
from app.tickets.ws import ConnectionManager

@asynccontextmanager
async def lifespan(app: FastAPI):
    pool = get_redis_pool()
    redis = Redis(connection_pool=pool)
    manager = ConnectionManager(redis)
    await manager.startup()
    app.state.connection_manager = manager
    setup_logging()
    
    yield

    await redis.aclose()
    await pool.aclose()


def create_app(*args, **kwargs) -> FastAPI:
    app = FastAPI(*args, **kwargs)

    app.include_router(users_router)
    app.include_router(auth_router)
    app.include_router(ticket_router)
    register_exception_handlers(app)

    return app

app = create_app(lifespan=lifespan)

logger = logging.getLogger(__name__)

@app.middleware("http")
async def timing_middleware(request: Request, call_next: Callable[[Request], Awaitable[Response]]):
    start = time.perf_counter()
    response = await call_next(request)
    duration = time.perf_counter() - start
    logger.info(f"{request.method} {request.url.path} completed in {format_duration(duration)}"
                f" | status={response.status_code}")
    return response