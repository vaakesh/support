from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.users.models import User
from app.users.errors import UserNotFoundError



async def get_user_by_uuid_or_error(
        user_uuid: UUID,
        session: AsyncSession,
) -> User:
    stmt = select(User).where(User.uuid == user_uuid)
    result = await session.execute(stmt)
    user = result.scalar_one_or_none()

    if user is None:
        raise UserNotFoundError()
    
    return user