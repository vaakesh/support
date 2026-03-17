import logging

from fastapi import APIRouter, FastAPI

from app.auth.router import router as auth_router
from app.exception_handlers import register_exception_handlers
from app.users.router import router as users_router

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(filename)s:%(lineno)d | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)

def create_app() -> FastAPI:

    app = FastAPI(debug=False)

    app.include_router(users_router)
    app.include_router(auth_router)
    register_exception_handlers(app)

    return app

app = create_app()