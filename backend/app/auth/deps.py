from uuid import UUID

from fastapi import Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.errors import AccessTokenNotFoundError
from app.auth.schemas import ClientInfo
from app.auth.service import AuthRepository, AuthService, auth_token_service
from app.deps import get_session
from app.users.deps import get_user_service
from app.users.models import User
from app.users.service import UserRepository, UserService


def get_auth_service(
    session: AsyncSession = Depends(get_session),
) -> AuthService:
    auth_repo = AuthRepository(session)
    user_repo = UserRepository(session)
    return AuthService(session, auth_repo, user_repo, auth_token_service)


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
