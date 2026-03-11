from fastapi import Request, Response

from app.auth.errors import RefreshTokenNotFoundError
from app.auth.service import auth_token_config


def set_tokens_cookie(access_token: str, refresh_token: str, response: Response) -> None:
    response.set_cookie(
        key="access_token",
        value=access_token,
        httponly=True,
        secure=True,
        samesite="none",
        max_age=60 * auth_token_config.access_token_expire_minutes,
    )
    response.set_cookie(
        key="refresh_token",
        value=refresh_token,
        httponly=True,
        secure=True,
        samesite="none",
        max_age=60 * auth_token_config.refresh_token_expire_days,
    )


def clear_tokens_cookie(response: Response) -> None:
    response.delete_cookie(key="access_token")
    response.delete_cookie(key="refresh_token")


def get_refresh_cookie(request: Request) -> str:
    refresh_token = request.cookies.get("refresh_token")
    if refresh_token is None:
        raise RefreshTokenNotFoundError()

    return refresh_token
