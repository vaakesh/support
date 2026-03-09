from fastapi import FastAPI, APIRouter
from app.users.router import router as users_router
from app.exception_handlers import register_exception_handlers


app = FastAPI()

router = APIRouter()

@router.get("/health")
async def health():
    return {"healthy": "ok"}

app.include_router(router)
app.include_router(users_router)
register_exception_handlers(app)