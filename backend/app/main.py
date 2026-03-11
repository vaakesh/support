from fastapi import APIRouter, FastAPI

from app.auth.router import router as auth_router
from app.exception_handlers import register_exception_handlers
from app.users.router import router as users_router

app = FastAPI(debug=False)

router = APIRouter()


@router.get("/health")
async def health():
    return {"healthy": "ok"}


app.include_router(router)
app.include_router(users_router)
app.include_router(auth_router)
register_exception_handlers(app)
