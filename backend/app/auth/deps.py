import logging
from functools import lru_cache
from uuid import UUID

from fastapi import Depends, Request, WebSocket, WebSocketDisconnect
from fastapi.security import OAuth2PasswordBearer

from app.auth.errors import AccessTokenNotFoundError
from app.auth.schemas import BearerToken, ClientInfo
from app.auth.service import AuthService, AuthTokenService, get_auth_token_config
from app.deps import get_uow
from app.service import UnitOfWork
from app.users.deps import get_user_service
from app.users.models import User
from app.users.service import UserService


@lru_cache
def get_auth_token_service() -> AuthTokenService:
    return AuthTokenService(get_auth_token_config())

def get_auth_service(
    auth_token_service: AuthTokenService = Depends(get_auth_token_service),
    uow: UnitOfWork = Depends(get_uow),
) -> AuthService:
    return AuthService(uow, auth_token_service)

# auto_error = False, чтобы не выкидывалась ошибка, если bearer токен не найден
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/token", auto_error=False)
async def get_bearer_token(token: str = Depends(oauth2_scheme)) -> BearerToken | None:
    """
    returns bearer token if found else None
    """
    return token

async def auth_user(
    request: Request,
    bearer_token: str | None = Depends(get_bearer_token),
) -> str:
    """
    checks user's bearer token first, then access token from cookie;
    if found none of them raises exception
    """
    if bearer_token is not None:
        return bearer_token
    

    access_token = request.cookies.get("access_token")

    if access_token is None:
        raise AccessTokenNotFoundError()
    
    return access_token

async def auth_user_ws(
    websocket: WebSocket,
) -> str:
    access_token = websocket.cookies.get("access_token")

    if not access_token:
        await websocket.close(code=1008)
        raise WebSocketDisconnect(code=1008)
    
    return access_token
    

async def get_current_user(
    user_service: UserService = Depends(get_user_service),
    access_token: str = Depends(auth_user),
    auth_token_service: AuthTokenService = Depends(get_auth_token_service)
) -> User:
    """
    returns user by access token
    """
    
    payload = auth_token_service.decode_access_token(access_token)
    user_uuid = UUID(payload.get("sub"))

    user = await user_service.get_by_uuid(user_uuid)
    return user

async def get_current_user_ws(
    user_service: UserService = Depends(get_user_service),
    access_token: str = Depends(auth_user_ws),
    auth_token_service: AuthTokenService = Depends(get_auth_token_service)
) -> User:
    """
    returns user by access token for websocket
    """
    
    payload = auth_token_service.decode_access_token(access_token)
    user_uuid = UUID(payload.get("sub"))

    user = await user_service.get_by_uuid(user_uuid)
    return user

def get_client_info(request: Request) -> ClientInfo:
    return ClientInfo(
        user_agent=request.headers.get("user-agent"),
        ip=request.client.host if request.client else None,
    )
