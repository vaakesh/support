from fastapi import Depends

from app.deps import get_uow
from app.service import UnitOfWork
from app.users.service import UserService


def get_user_service(uow: UnitOfWork = Depends(get_uow)) -> UserService:
    return UserService(uow)
