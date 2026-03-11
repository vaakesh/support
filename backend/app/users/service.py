from uuid import UUID

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.utils import hash_password
from app.users.errors import UserAlreadyExistsError, UserNotFoundError
from app.users.models import User


class UserService:
    def __init__(
        self,
        session: AsyncSession,
        user_repo: UserRepository,
    ) -> None:
        self.session = session
        self.user_repo = user_repo

    async def get_by_uuid(self, user_uuid: UUID) -> User:
        """
        Returns user by uuid or raises exception
        """
        user = await self.user_repo.get_by_uuid(user_uuid)
        if user is None:
            raise UserNotFoundError()
        return user

    async def get_by_username(self, username: str) -> User:
        """
        Returns user by username or raises exception
        """
        user = await self.user_repo.get_by_username(username)
        if user is None:
            raise UserNotFoundError()
        return user

    async def get_by_id(self, user_id: int) -> User:
        """
        Returns user by id or raises exception
        """
        user = await self.user_repo.get_by_id(user_id)
        if user is None:
            raise UserNotFoundError()
        return user

    async def get_by_email(self, email: str) -> User:
        """
        Returns user by email or raises exception
        """
        user = await self.user_repo.get_by_email(email)
        if user is None:
            raise UserNotFoundError()
        return user

    async def create_user(
        self,
        username: str,
        email: str,
        password: str,
    ) -> User:
        user = User(
            username=username,
            email=email,
            hashed_password=hash_password(password),
        )
        self.session.add(user)

        try:
            await self.session.commit()
        except IntegrityError as e:
            await self.session.rollback()
            raise UserAlreadyExistsError() from e
        except Exception:
            await self.session.rollback()
            raise

        await self.session.refresh(user)

        return user

    async def update_user(
        self,
        user_uuid: UUID,
        username: str | None = None,
        email: str | None = None,
        password: str | None = None,
    ) -> User:
        updated = False
        user = await self.get_by_uuid(user_uuid)

        if username is not None and username != user.username:
            user.username = username
            updated = True

        if email is not None and email != user.email:
            user.email = email
            updated = True

        if password is not None:
            user.hashed_password = hash_password(password)
            updated = True

        if not updated:
            return user
        try:
            await self.session.commit()
        except IntegrityError as e:
            await self.session.rollback()
            raise UserAlreadyExistsError() from e
        except Exception:
            await self.session.rollback()
            raise

        await self.session.refresh(user)

        return user

    async def delete_user(self, user_uuid: UUID) -> None:
        user = await self.get_by_uuid(user_uuid)

        await self.session.delete(user)
        try:
            await self.session.commit()
        except Exception:
            await self.session.rollback()
            raise


class UserRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_by_username(self, username: str) -> User | None:
        stmt = select(User).where(User.username == username)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_uuid(self, user_uuid: UUID) -> User | None:
        stmt = select(User).where(User.uuid == user_uuid)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_id(self, user_id: int) -> User | None:
        stmt = select(User).where(User.id == user_id)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_email(self, user_email: str) -> User | None:
        stmt = select(User).where(User.email == user_email)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()
