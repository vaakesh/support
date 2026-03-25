import logging
from uuid import UUID

from redis.asyncio import Redis
from sqlalchemy.exc import IntegrityError

from app.auth.utils import hash_password
from app.service import UnitOfWork
from app.users.errors import PermissionDeniedError, UserAlreadyExistsError, UserNotFoundError
from app.users.models import User
from app.users.schemas import UserCreate, UserOut, UserSchema, UserUpdate

logger = logging.getLogger(__name__)

class UserService:
    def __init__(self, uow: UnitOfWork, redis: Redis) -> None:
        self.uow = uow
        self.redis = redis

    async def get_by_uuid(self, user_uuid: UUID) -> UserSchema:
        """
        Returns user by uuid or raises exception
        """
        cache_key = f"user:{user_uuid}"
        cached = await self.redis.get(cache_key)
        if cached:
            return UserSchema.model_validate_json(cached)
        
        async with self.uow as uow:
            user = await self._get_user_by_uuid(uow, user_uuid)
            user = UserSchema.model_validate(user)

            await self.redis.setex(cache_key, 300, user.model_dump_json())
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
        payload: UserCreate,
    ) -> UserSchema:
        """
        creates and returns user or raises exception if user exists
        """
        try:
            async with self.uow as uow:
                user_data = payload.model_dump(exclude={"password"})
                user = User(
                    **user_data,
                    hashed_password=hash_password(payload.password),
                )
                uow.user_repo.add(user)
                await uow.commit()
                await uow.user_repo.refresh(user)
                return UserSchema.model_validate(user)
        except IntegrityError as e:
            raise UserAlreadyExistsError() from e

    async def update_user(
        self,
        current_user: User,
        target_user_uuid: UUID,
        payload: UserUpdate,
    ) -> UserSchema:
        if current_user.uuid != target_user_uuid and not current_user.is_admin:
            raise PermissionDeniedError()
        try:
            async with self.uow as uow:
                user = await uow.user_repo.get_by_uuid_for_update(target_user_uuid)
                if user is None:
                    raise UserNotFoundError()
                update_data = payload.model_dump(exclude_unset=True)
                updated = False

                if "username" in update_data and update_data["username"] != user.username:
                    user.username = update_data["username"]
                    updated = True

                if "email" in update_data and update_data["email"] != user.email:
                    user.email = update_data["email"]
                    updated = True

                if "password" in update_data:
                    user.hashed_password = hash_password(update_data["password"])
                    updated = True

                if updated:
                    await uow.commit()
                    cache_key = f"user:{target_user_uuid}"
                    await self.redis.delete(cache_key)

                return UserSchema.model_validate(user)
        except IntegrityError as e:
            raise UserAlreadyExistsError() from e

    async def delete_user(self, current_user: User, user_uuid: UUID) -> None:
        if current_user.uuid != user_uuid and not current_user.is_admin:
            raise PermissionDeniedError()
        
        async with self.uow as uow:
            user = await uow.user_repo.get_by_uuid_for_update(user_uuid)
            if user is None:
                return
            await uow.user_repo.delete(user)
            await uow.commit()
            cache_key = f"user:{user_uuid}"
            await self.redis.delete(cache_key)
