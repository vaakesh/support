from uuid import UUID

from fastapi import Depends, Request

from app.auth.errors import AccessTokenNotFoundError
from app.auth.schemas import ClientInfo
from app.auth.service import AuthService, AuthTokenService, auth_token_service
from app.deps import get_uow
from app.service import UnitOfWork
from app.users.deps import get_user_service
from app.users.models import User
from app.users.service import UserService


def get_auth_token_service() -> AuthTokenService:
    return auth_token_service


def get_auth_service(
    auth_token_service: AuthTokenService = Depends(get_auth_token_service),
    uow: UnitOfWork = Depends(get_uow),
) -> AuthService:
    return AuthService(uow, auth_token_service)


async def get_current_user(
    request: Request,
    user_service: UserService = Depends(get_user_service),
) -> User:
    token = request.cookies.get("access_token")

    if not token:
        raise AccessTokenNotFoundError()

    payload = auth_token_service.decode_access_token(token)
    user_uuid = UUID(payload.get("sub"))

    user = await user_service.get_by_uuid(user_uuid)
    return user


def get_client_info(request: Request) -> ClientInfo:
    return ClientInfo(
        user_agent=request.headers.get("user-agent"),
        ip=request.client.host if request.client else None,
    )
