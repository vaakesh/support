from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from app.auth.errors import InvalidTokenError
from app.users.errors import PermissionDeniedError, UserAlreadyExistsError, UserNotFoundError
from app.errors import TooManyRequestsError


async def user_not_found_handler(
    request: Request,
    exc: UserNotFoundError,
):
    return JSONResponse(
        status_code=status.HTTP_404_NOT_FOUND,
        content={
            "message": str(exc),
        },
    )


async def user_already_exists_handler(
    request: Request,
    exc: UserAlreadyExistsError,
):
    return JSONResponse(
        status_code=status.HTTP_409_CONFLICT,
        content={
            "message": str(exc),
        },
    )

async def permission_denied_handler(
    request: Request,
    exc: PermissionDeniedError,
):
    return JSONResponse(
        status_code=status.HTTP_403_FORBIDDEN,
        content={
            "message": str(exc),
        },
    )


async def invalid_token_handler(request: Request, exc: InvalidTokenError):
    return JSONResponse(
        status_code=status.HTTP_401_UNAUTHORIZED,
        content={
            "message": str(exc),
        },
    )


async def unhandled_exception_handler(request: Request, exc: Exception):
    return JSONResponse(
        status_code=500,
        content={
            "message": "Internal server error",
        },
    )


async def request_validation_handler(request: Request, exc: RequestValidationError):
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
        content={
            "message": "Validation error",
            "details": exc.errors(),
        },
    )

async def too_many_requests_handler(request: Request, exc: TooManyRequestsError):
    return JSONResponse(
        status_code=status.HTTP_429_TOO_MANY_REQUESTS,
        content={
            "message": str(exc),
        },
    )


def register_exception_handlers(app: FastAPI):
    app.add_exception_handler(UserNotFoundError, user_not_found_handler)
    app.add_exception_handler(UserAlreadyExistsError, user_already_exists_handler)
    app.add_exception_handler(InvalidTokenError, invalid_token_handler)
    app.add_exception_handler(Exception, unhandled_exception_handler)
    app.add_exception_handler(PermissionDeniedError, permission_denied_handler)
    app.add_exception_handler(RequestValidationError, request_validation_handler)
    app.add_exception_handler(TooManyRequestsError, too_many_requests_handler)