from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.deps import get_session
from app.users.service import UserRepository, UserService


def get_user_service(
    session: AsyncSession = Depends(get_session),
) -> UserService:
    user_repo = UserRepository(session)
    return UserService(session, user_repo)
