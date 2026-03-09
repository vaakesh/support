from fastapi import Request, FastAPI
from fastapi.responses import JSONResponse

from app.users.errors import UserAlreadyExistsError, UserNotFoundError




async def user_not_found_handler(
    request: Request,
    exc: UserNotFoundError,
):
    return JSONResponse(
        status_code=404,
        content={
            "message": "User not found"
        },
    )

async def user_already_exists_handler(
        request: Request,
        exc: UserAlreadyExistsError,
):
    return JSONResponse(
        status_code=404,
        content={
            "message": "Username or email is already in use"
        },
    )


def register_exception_handlers(app: FastAPI):
    app.add_exception_handler(UserNotFoundError, user_not_found_handler)
    app.add_exception_handler(UserAlreadyExistsError, user_already_exists_handler)