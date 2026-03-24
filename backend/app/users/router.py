import logging
from uuid import UUID

from fastapi import APIRouter, Depends, Request, Response, status

from app.auth.deps import get_current_user
from app.users.deps import get_user_service
from app.users.models import User
from app.users.schemas import UserCreate, UserMe, UserOut, UserUpdate
from app.users.service import UserService
from app.utils import RateLimit



router = APIRouter(prefix="/users")


@router.get("/me", response_model=UserMe)
async def get_me(
    request: Request,
    current_user: User = Depends(get_current_user),
    _: None = Depends(RateLimit(5, 60)),
):
    return current_user


@router.get("/{user_uuid}", response_model=UserOut)
async def get_public_user(
    user_uuid: UUID,
    user_service: UserService = Depends(get_user_service),
):
    return await user_service.get_by_uuid(user_uuid)


@router.post("/", response_model=UserOut, status_code=status.HTTP_201_CREATED)
async def create_user(
    payload: UserCreate,
    user_service: UserService = Depends(get_user_service),
) -> User:
    user = await user_service.create_user(payload)
    return user


@router.patch("/{user_uuid}", response_model=UserOut, status_code=status.HTTP_200_OK)
async def update_user(
    user_uuid: UUID,
    payload: UserUpdate,
    current_user: User = Depends(get_current_user),
    user_service: UserService = Depends(get_user_service),
):
    user = await user_service.update_user(
        current_user,
        user_uuid,
        payload,
    )
    return user


@router.delete("/{user_uuid}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_user(
    user_uuid: UUID,
    current_user: User = Depends(get_current_user),
    user_service: UserService = Depends(get_user_service),
):
    await user_service.delete_user(current_user, user_uuid)
    return Response(status_code=status.HTTP_204_NO_CONTENT)