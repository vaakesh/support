import hashlib
import hmac
import secrets
from datetime import timedelta
from typing import Any
from uuid import UUID

import jwt
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.errors import (
    InvalidTokenError,
    InvalidTokenTypeError,
)
from app.auth.models import UserSession
from app.auth.schemas import AuthTokenConfig, ClientInfo, IssuedTokens, TokenPair
from app.auth.utils import verify_password
from app.config import settings
from app.users.errors import UserNotFoundError
from app.users.models import User
from app.users.service import UserRepository
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

    def verify_refresh_token(self, token: str, token_hash: str) -> bool:
        expected = self.hash_refresh_token(token)
        return hmac.compare_digest(expected, token_hash)

    def issue_tokens(self, user_uuid: UUID) -> IssuedTokens:
        access_token = self.create_access_token(user_uuid)
        refresh_token = self.generate_refresh_token()
        refresh_token_hash = self.hash_refresh_token(refresh_token)

        return IssuedTokens(
            access_token=access_token,
            refresh_token=refresh_token,
            refresh_token_hash=refresh_token_hash,
        )


auth_token_config = AuthTokenConfig(
    private_key=settings.auth_jwt.private_key_path.read_text(encoding="utf-8"),
    public_key=settings.auth_jwt.public_key_path.read_text(encoding="utf-8"),
    algorithm=settings.auth_jwt.algorithm,
    access_token_expire_minutes=settings.auth_jwt.access_token_expire_minutes,
    refresh_token_expire_days=settings.auth_jwt.refresh_token_expire_days,
    refresh_pepper_bytes=settings.refresh_pepper.encode("utf-8"),
)

auth_token_service = AuthTokenService(auth_token_config)


class AuthService:
    def __init__(
        self,
        session: AsyncSession,
        auth_repo: AuthRepository,
        user_repo: UserRepository,
        auth_token_service: AuthTokenService,
    ):
        self.session = session
        self.auth_repo = auth_repo
        self.user_repo = user_repo
        self.auth_token_service = auth_token_service

    async def login(
        self,
        username: str,
        password: str,
        client_info: ClientInfo,
    ) -> TokenPair:
        user = await self.authenticate_user(
            username,
            password,
        )
        tokens = self.auth_token_service.issue_tokens(user.uuid)
        user_session = self.build_user_session(user, tokens.refresh_token_hash, client_info)
        self.session.add(user_session)

        try:
            await self.session.commit()
        except Exception:
            await self.session.rollback()
            raise

        await self.session.refresh(user_session)

        return TokenPair(tokens.access_token, tokens.refresh_token)

    async def logout(
        self,
        user: User,
        refresh_token: str,
    ) -> None:
        user_session = await self.validate_refresh_token(refresh_token)
        if user_session.user_id != user.id:
            raise InvalidTokenError()

        user_session.revoked_at = utcnow()

        try:
            await self.session.commit()
        except Exception:
            await self.session.rollback()
            raise

    async def authenticate_user(
        self,
        username: str,
        password: str,
    ) -> User:
        user = await self.user_repo.get_by_username(username)
        if not user or not verify_password(password, user.hashed_password):
            raise UserNotFoundError()

        return user

    async def refresh(
        self,
        refresh_token: str,
        client_info: ClientInfo,
    ) -> TokenPair:
        user_session = await self.validate_refresh_token(refresh_token)
        user = await self.user_repo.get_by_id(user_session.user_id)
        tokens = self.auth_token_service.issue_tokens(user.uuid)
        new_user_session = self.build_user_session(
            user, tokens.refresh_token_hash, client_info
        )

        self.session.add(new_user_session)
        await self.session.flush()
        user_session.replaced_by_session_id = new_user_session.id
        try:
            await self.session.commit()
        except Exception:
            await self.session.rollback()
            raise

        return TokenPair(tokens.access_token, tokens.refresh_token)

    async def validate_refresh_token(self, refresh_token: str) -> UserSession:
        """
        returns a valid user session by refresh token or raises exception
        """
        refresh_token_hash = self.auth_token_service.hash_refresh_token(refresh_token)
        user_session = await self.auth_repo.get_user_session(refresh_token_hash)

        if (
            user_session is None
            or user_session.revoked_at is not None
            or user_session.replaced_by_session_id is not None
            or user_session.expires_at <= utcnow()
        ):
            raise InvalidTokenError()

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

    async def get_all_users_sessions(self, user: User) -> list[UserSession]:
        return await self.auth_repo.get_all_user_sessions(user.id)


class AuthRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_user_session(self, refresh_token_hash: str) -> UserSession:
        stmt = (
            select(UserSession)
            .where(UserSession.refresh_token_hash == refresh_token_hash)
            .with_for_update()
        )
        result = await self.session.execute(stmt)
        user_session = result.scalar_one_or_none()
        return user_session

    async def get_all_user_sessions(self, user_id: int) -> list[UserSession]:
        sessions = (
            (
                await self.session.execute(
                    select(UserSession).where(
                        UserSession.user_id == user_id,
                    )
                )
            )
            .scalars()
            .all()
        )
        return sessions
