from functools import lru_cache
import hashlib
import hmac
import secrets
from datetime import timedelta
from typing import Any
from uuid import UUID

import jwt

from app.auth.errors import (
    InvalidTokenError,
    InvalidTokenTypeError,
)
from app.auth.models import UserSession
from app.auth.schemas import AuthTokenConfig, BearerToken, ClientInfo, IssuedTokens, TokenPair
from app.auth.utils import verify_password
from app.config import get_settings
from app.service import UnitOfWork
from app.users.errors import UserNotFoundError
from app.users.models import User
from app.utils import utcnow


class AuthTokenService:
    def __init__(self, config: AuthTokenConfig) -> None:
        self.config = config

    def create_access_token(self, user_uuid: UUID) -> str:
        now = utcnow()
        payload: dict[str, Any] = {
            "sub": str(user_uuid),
            "type": "access",
            "iat": int(now.timestamp()),
            "exp": int(
                (
                    now + timedelta(minutes=self.config.access_token_expire_minutes)
                ).timestamp()
            ),
            "jti": secrets.token_hex(16),
        }
        return jwt.encode(
            payload=payload,
            key=self.config.private_key,
            algorithm=self.config.algorithm,
        )

    def decode_access_token(self, token: str) -> dict[str, Any]:
        """
        returns payload if access token is valid else raises exception
        """
        try:
            payload = jwt.decode(
                token,
                key=self.config.public_key,
                algorithms=[self.config.algorithm],
            )
        except jwt.InvalidTokenError as e:
            raise InvalidTokenError() from e

        if payload.get("type") != "access":
            raise InvalidTokenTypeError()

        return payload

    def generate_refresh_token(self) -> str:
        return secrets.token_urlsafe(64)

    def hash_refresh_token(self, token: str) -> str:
        return hmac.new(
            self.config.refresh_pepper_bytes, token.encode(), hashlib.sha256
        ).hexdigest()

    def issue_tokens(self, user_uuid: UUID) -> IssuedTokens:
        access_token = self.create_access_token(user_uuid)
        refresh_token = self.generate_refresh_token()
        refresh_token_hash = self.hash_refresh_token(refresh_token)

        return IssuedTokens(
            access_token=access_token,
            refresh_token=refresh_token,
            refresh_token_hash=refresh_token_hash,
        )


@lru_cache()
def get_auth_token_config() -> AuthTokenConfig:
    settings = get_settings()

    return AuthTokenConfig(
        private_key=settings.auth_jwt.private_key_path.read_text(encoding="utf-8"),
        public_key=settings.auth_jwt.public_key_path.read_text(encoding="utf-8"),
        algorithm=settings.auth_jwt.algorithm,
        access_token_expire_minutes=settings.auth_jwt.access_token_expire_minutes,
        refresh_token_expire_days=settings.auth_jwt.refresh_token_expire_days,
        refresh_pepper_bytes=settings.refresh_pepper.encode("utf-8"),
    )


class AuthService:
    def __init__(self, uow: UnitOfWork, auth_token_service: AuthTokenService):
        self.uow = uow
        self.auth_token_service = auth_token_service

    async def login(
        self,
        username: str,
        password: str,
        client_info: ClientInfo,
    ) -> TokenPair:
        async with self.uow as uow:
            user = await self._authenticate_user(
                username,
                password,
                uow,
            )
            tokens = self.auth_token_service.issue_tokens(user.uuid)
            user_session = self.build_user_session(
                user, tokens.refresh_token_hash, client_info
            )
            uow.auth_repo.add(user_session)

            await uow.commit()

            await uow.auth_repo.refresh(user_session)

            return TokenPair(tokens.access_token, tokens.refresh_token)
        
    async def login_by_bearer_token_without_refresh(self, username: str, password: str) -> BearerToken:
        async with self.uow as uow:
            user = await self._authenticate_user(
                username,
                password,
                uow,
            )
            bearer_access_token = self.auth_token_service.create_access_token(user.uuid)
            return BearerToken(bearer_access_token)

    async def logout(
        self,
        refresh_token: str | None = None,
    ) -> None:
        if not refresh_token:
            return
        revoked_at = utcnow()
        async with self.uow as uow:
            refresh_token_hash = self.auth_token_service.hash_refresh_token(refresh_token)
            is_updated = await uow.auth_repo.revoke_active_session_by_refresh_token_hash(refresh_token_hash, revoked_at)
            if is_updated:
                await uow.commit()

    async def _authenticate_user(
        self,
        username: str,
        password: str,
        uow: UnitOfWork,
    ) -> User:
        user = await uow.user_repo.get_by_username(username)
        if not user or not verify_password(password, user.hashed_password):
            raise UserNotFoundError()

        return user

    async def refresh(
        self,
        refresh_token: str,
        client_info: ClientInfo,
    ) -> TokenPair:
        async with self.uow as uow:
            user_session = await self._validate_refresh_token(refresh_token, uow)
            user = await uow.user_repo.get_by_id(user_session.user_id)
            if user is None:
                raise UserNotFoundError()
            tokens = self.auth_token_service.issue_tokens(user.uuid)
            new_user_session = self.build_user_session(
                user, tokens.refresh_token_hash, client_info
            )
            uow.auth_repo.add(new_user_session)
            await uow.auth_repo.flush()
            user_session.replaced_by_session_id = new_user_session.id
            user_session.revoked_at = utcnow()

            await uow.commit()

            return TokenPair(tokens.access_token, tokens.refresh_token)

    async def _validate_refresh_token(
        self, refresh_token: str, uow: UnitOfWork
    ) -> UserSession:
        """
        returns a valid user session by refresh token or raises exception
        """
        refresh_token_hash = self.auth_token_service.hash_refresh_token(refresh_token)
        user_session = await uow.auth_repo.get_user_session_by_refresh(refresh_token_hash, for_update=True)

        if (
            user_session is None
            or user_session.revoked_at is not None
            or user_session.replaced_by_session_id is not None
            or user_session.expires_at <= utcnow()
        ):
            raise InvalidTokenError("Session expired")

        return user_session

    def build_user_session(
        self, user: User, refresh_token_hash: str, client_info: ClientInfo
    ) -> UserSession:
        user_session = UserSession(
            user_id=user.id,
            refresh_token_hash=refresh_token_hash,
            expires_at=utcnow()
            + timedelta(days=self.auth_token_service.config.refresh_token_expire_days),
            user_agent=client_info.user_agent,
            ip=client_info.ip,
        )
        return user_session

    async def get_all_user_sessions(self, user_id: int) -> list[UserSession]:
        async with self.uow as uow:
            return await uow.auth_repo.get_all_user_sessions(user_id)
