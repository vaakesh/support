from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.deps import hash_password
from app.deps import get_session
from app.users.schemas import UserCreate, UserOut, UserUpdate
from app.users.service import (
    svc_create_user,
    svc_delete_user,
    svc_read_user,
    svc_update_user,
)

router = APIRouter(prefix="/users")


@router.get("/{user_uuid}", response_model=UserOut)
async def read_user(user_uuid: UUID, session: AsyncSession = Depends(get_session)):
    return await svc_read_user(user_uuid, session)
    
@router.post("/", response_model=UserOut, status_code=status.HTTP_201_CREATED)
async def create_user(
    payload: UserCreate,
    session: AsyncSession = Depends(get_session),
):
    user = await svc_create_user(
        session=session,
        username=payload.username,
        email=payload.email,
        password=payload.password
    )
    return user
    

@router.patch("/{user_uuid}", response_model=UserOut)
async def update_user(
    user_uuid: UUID,
    payload: UserUpdate,
    session: AsyncSession = Depends(get_session),
):
    user = await svc_update_user(
        user_uuid=user_uuid,
        session=session,
        username=payload.username,
        email=payload.email,
        password=payload.password,
    )
    return user
    
@router.delete("/{user_uuid}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_user(
    user_uuid: UUID,
    session: AsyncSession = Depends(get_session),
):
    await svc_delete_user(user_uuid, session)
    return Response(status_code=204)