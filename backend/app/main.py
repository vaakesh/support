from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.responses import HTMLResponse

import app.models  # noqa: F401 # sqlalchemy models registration
from app.auth.router import router as auth_router
from app.exception_handlers import register_exception_handlers
from app.logging_config import setup_logging
from app.users.router import router as users_router
from app.tickets.router import router as ticket_router

@asynccontextmanager
async def lifespan(app: FastAPI):
    yield


def create_app(*args, **kwargs) -> FastAPI:
    app = FastAPI(*args, **kwargs)

    app.include_router(users_router)
    app.include_router(auth_router)
    app.include_router(ticket_router)
    register_exception_handlers(app)

    return app

setup_logging()
app = create_app(lifespan=lifespan)
