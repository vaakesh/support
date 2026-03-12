from uuid import UUID

from sqlalchemy.exc import IntegrityError

from app.auth.utils import hash_password
from app.service import UnitOfWork
from app.users.errors import UserAlreadyExistsError, UserNotFoundError
from app.users.models import User


class UserService:
    def __init__(self, uow: UnitOfWork) -> None:
        self.uow = uow

    async def get_by_uuid(self, user_uuid: UUID) -> User:
        """
        Returns user by uuid or raises exception
        """
        async with self.uow as uow:
            user = await uow.user_repo.get_by_uuid(user_uuid)
            if user is None:
                raise UserNotFoundError(f"User with uuid={user_uuid} not found")
            return user

    async def get_by_username(self, username: str) -> User:
        """
        Returns user by username or raises exception
        """
        async with self.uow as uow:
            user = await uow.user_repo.get_by_username(username)
            if user is None:
                raise UserNotFoundError(f"User with username={username} not found")
            return user

    async def get_by_id(self, user_id: int) -> User:
        """
        Returns user by id or raises exception
        """
        async with self.uow as uow:
            user = await uow.user_repo.get_by_id(user_id)
            if user is None:
                raise UserNotFoundError(f"User with id={user_id} not found")
            return user

    async def get_by_email(self, email: str) -> User:
        """
        Returns user by email or raises exception
        """
        async with self.uow as uow:
            user = await uow.user_repo.get_by_email(email)
            if user is None:
                raise UserNotFoundError(f"User with email={email} not found")
            return user

    async def _get_user_by_uuid(self, uow: UnitOfWork, user_uuid: UUID) -> User:
        user = await uow.user_repo.get_by_uuid(user_uuid)
        if user is None:
            raise UserNotFoundError(f"User with uuid={user_uuid} not found")
        return user

    async def create_user(
        self,
        username: str,
        email: str,
        password: str,
    ) -> User:
        """
        creates and returns user or raises exception if user exists
        """
        try:
            async with self.uow as uow:
                user = User(
                    username=username,
                    email=email,
                    hashed_password=hash_password(password),
                )
                uow.user_repo.add(user)
                await uow.commit()
                await uow.user_repo.refresh(user)
                return user
        except IntegrityError as e:
            raise UserAlreadyExistsError() from e

    async def update_user(
        self,
        user_uuid: UUID,
        username: str | None = None,
        email: str | None = None,
        password: str | None = None,
    ) -> User:
        try:
            async with self.uow as uow:
                updated = False
                user = await self._get_user_by_uuid(uow, user_uuid)

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

                await uow.commit()
                await uow.user_repo.refresh(user)

                return user
        except IntegrityError as e:
            raise UserAlreadyExistsError() from e

    async def delete_user(self, user_uuid: UUID) -> None:
        async with self.uow as uow:
            user = await self._get_user_by_uuid(uow, user_uuid)
            await uow.user_repo.delete(user)
            await uow.commit()
