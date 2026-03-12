from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.repository import AbstractRepository
from app.users.models import User


class UserRepository(AbstractRepository[User]):
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_by_id(self, user_id: int) -> User | None:
        return await self.session.get(User, user_id)

    def add(self, user: User) -> None:
        self.session.add(user)

    async def delete(self, user: User) -> None:
        await self.session.delete(user)

    async def refresh(self, user: User) -> None:
        await self.session.refresh(user)

    async def get_by_username(self, username: str) -> User | None:
        stmt = select(User).where(User.username == username)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_uuid(self, user_uuid: UUID) -> User | None:
        stmt = select(User).where(User.uuid == user_uuid)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_email(self, user_email: str) -> User | None:
        stmt = select(User).where(User.email == user_email)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()
