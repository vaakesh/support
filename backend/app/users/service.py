from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import IntegrityError
from app.users.models import User
from app.users.schemas import UserCreate
from app.auth.deps import hash_password
from app.users.deps import get_user_by_uuid_or_error
from app.users.errors import UserAlreadyExistsError


async def svc_read_user(user_uuid: UUID, session: AsyncSession) -> User:
    return await get_user_by_uuid_or_error(user_uuid, session)


async def svc_create_user(
    session: AsyncSession,
    username: str,
    email: str,
    password: str,
) -> User:
    # stmt = select(User).where(
    #     (User.username == username) | (User.email == email)
    # )
    # result = await session.execute(stmt)
    # existing_user = result.scalar_one_or_none()

    # if existing_user:
    #     raise UserAlreadyExistsError()
    
    user = User(
        username=username,
        email=email,
        hashed_password=hash_password(password),
    )

    session.add(user)
    try:
        await session.commit()
    except IntegrityError:
        await session.rollback()
        raise UserAlreadyExistsError()
    
    await session.refresh(user)
    
    return user


async def svc_update_user(
        user_uuid: UUID,
        session: AsyncSession,
        username: str | None = None,
        email: str | None = None,
        password: str | None = None,
) -> User:
    user = await get_user_by_uuid_or_error(user_uuid, session)
    
    if username is not None and username != user.username:
        stmt = select(User).where(User.username == username, User.uuid != user.uuid)
        result = await session.execute(stmt)
        existing_user = result.scalar_one_or_none()

        if existing_user:
            raise UserAlreadyExistsError()
        
        user.username = username

    if email is not None and email != user.email:
        stmt = select(User).where(User.email == email, User.uuid != user.uuid)
        result = await session.execute(stmt)
        existing_user = result.scalar_one_or_none()

        if existing_user:
            raise UserAlreadyExistsError()
        
        user.email = email

    if password is not None:
        user.hashed_password = hash_password(password)

    try:
        await session.commit()
    except IntegrityError as e:
        await session.rollback()
        raise UserAlreadyExistsError()

    await session.refresh(user)

    return user

async def svc_delete_user(user_uuid: UUID, session: AsyncSession) -> None:
    user = await get_user_by_uuid_or_error(user_uuid, session)
    
    await session.delete(user)
    try:
        await session.commit()
    except Exception:
        await session.rollback()
        raise