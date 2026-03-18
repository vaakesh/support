import logging

from fastapi import APIRouter, Depends, Request, Response
from fastapi.security import OAuth2PasswordRequestForm

from app.auth.cookies import clear_tokens_cookie, get_refresh_cookie, set_tokens_cookie
from app.auth.deps import get_auth_service, get_client_info, get_current_user
from app.auth.schemas import ClientInfo, SessionOut, TokenPair
from app.auth.service import AuthService
from app.users.models import User

router = APIRouter(prefix="/auth")

@router.post("/token")
async def login_for_bearer_token(
    form_data: OAuth2PasswordRequestForm = Depends(),
    auth_service: AuthService = Depends(get_auth_service),
):
    bearer_token = await auth_service.login_by_bearer_token_without_refresh(form_data.username, form_data.password)
    return bearer_token


@router.post("/login")
async def login(
    response: Response,
    form_data: OAuth2PasswordRequestForm = Depends(),
    auth_service: AuthService = Depends(get_auth_service),
    client_info: ClientInfo = Depends(get_client_info),
) -> None:
    tokens = await auth_service.login(form_data.username, form_data.password, client_info)
    set_tokens_cookie(tokens.access_token, tokens.refresh_token, response)


@router.post("/logout")
async def logout(
    response: Response,
    request: Request,
    auth_service: AuthService = Depends(get_auth_service),
) -> Response:
    refresh_token = request.cookies.get("refresh_token")
    await auth_service.logout(refresh_token)
    clear_tokens_cookie(response)


@router.post("/refresh")
async def refresh(
    response: Response,
    request: Request,
    auth_service: AuthService = Depends(get_auth_service),
    client_info: ClientInfo = Depends(get_client_info),
) -> TokenPair:
    refresh_token = get_refresh_cookie(request)
    tokens = await auth_service.refresh(refresh_token, client_info)
    set_tokens_cookie(tokens.access_token, tokens.refresh_token, response)
    return tokens


@router.get("/sessions", response_model=list[SessionOut])
async def get_sessions(
    user: User = Depends(get_current_user),
    auth_service: AuthService = Depends(get_auth_service),
) -> list[SessionOut]:
    sessions = await auth_service.get_all_user_sessions(user.id)
    return [SessionOut.model_validate(session) for session in sessions]
