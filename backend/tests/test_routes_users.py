import logging
from uuid import UUID, uuid4

import pytest
from fastapi import FastAPI, status

from app.auth.deps import get_current_user
from app.auth.utils import hash_password, verify_password
from app.users.deps import get_user_service
from app.users.errors import PermissionDeniedError, UserNotFoundError
from app.users.schemas import UserCreate, UserUpdate

logger = logging.getLogger(__name__)


class FakeUser:
    def __init__(self, username: str, email: str, hashed_password: str):
        self.id = 1
        self.uuid = uuid4()
        self.username = username
        self.email = email
        self.hashed_password = hashed_password
        self.is_admin = False
        self.is_active = False


@pytest.fixture
def fake_user_service():
    return FakeUserService()


@pytest.fixture
def override_user_service(app: FastAPI, fake_user_service):
    app.dependency_overrides[get_user_service] = lambda: fake_user_service
    yield
    app.dependency_overrides.pop(get_user_service, None)


@pytest.fixture
def override_get_current_user(app: FastAPI, current_user):
    app.dependency_overrides[get_current_user] = lambda: current_user
    yield
    app.dependency_overrides.pop(get_current_user, None)


@pytest.fixture
def current_user(fake_user_service) -> FakeUser:
    user = make_user(
        username="current_user",
        email="current@example.com",
        password="current_password",
    )
    saved_user = fake_user_service.add_user(user)
    return saved_user


class FakeUserService:
    def __init__(self):
        self.users = {}
        self.next_id = 1

    def _store_user(self, user):
        user.id = self.next_id
        self.next_id += 1
        self.users[user.uuid] = user
        return user

    def add_user(self, user: FakeUser) -> FakeUser:
        return self._store_user(user)

    async def create_user(self, payload: UserCreate) -> FakeUser:
        logger.info("FakeUserService.create_user called")
        user = FakeUser(
            username=payload.username,
            email=payload.email,
            hashed_password=hash_password(payload.password),
        )
        return self._store_user(user)

    async def update_user(
        self, current_user, user_uuid: UUID, payload: UserUpdate
    ) -> FakeUser:
        logger.info("FakeUserService.update_user called")
        if current_user.uuid != user_uuid and not current_user.is_admin:
            raise PermissionDeniedError()

        user = self.users.get(user_uuid)
        if not user:
            raise UserNotFoundError()

        update_data = payload.model_dump(exclude_unset=True)

        for field, value in update_data.items():
            if field == "password":
                user.hashed_password = hash_password(value)
            else:
                setattr(user, field, value)
        return user

    async def get_by_uuid(self, user_uuid: UUID) -> FakeUser:
        logger.info("FakeUserService.get_by_uuid called")
        user = self.users.get(user_uuid)
        if not user:
            raise UserNotFoundError()

        return user

    async def delete_user(self, current_user: FakeUser, user_uuid: UUID):
        logger.info("FakeUserService.delete_user called")
        if current_user.uuid != user_uuid and not current_user.is_admin:
            logger.warning("permission denied")
            raise PermissionDeniedError()

        user = self.users.get(user_uuid)
        if not user:
            logger.warning("user not found")
            raise UserNotFoundError()

        logger.info("deleting user")
        del self.users[user_uuid]

    def print_users(self) -> None:
        for user in self.users.values():
            print(user.username)


def make_user(
    username: str = "testuser",
    email: str = "test@example.com",
    password: str = "testpassword",
) -> FakeUser:
    return FakeUser(
        username=username,
        email=email,
        hashed_password=hash_password(password),
    )


@pytest.mark.asyncio
async def test_create_user_success(client, override_user_service):
    payload = {
        "username": "testuser",
        "email": "test@example.com",
        "password": "testpassword",
    }
    response = await client.post("/users/", json=payload)
    assert response.status_code == 201
    data = response.json()
    assert data["username"] == payload["username"]
    assert data["email"] == payload["email"]


@pytest.mark.asyncio
async def test_update_user_success(
    client, current_user, override_get_current_user, override_user_service
):
    update_payload = {
        "username": "updateduser",
        "email": "updated@example.com",
        "password": "new_password",
    }
    response = await client.patch(f"/users/{current_user.uuid}", json=update_payload)
    assert response.status_code == 200
    data = response.json()
    assert data["username"] == update_payload["username"]
    assert data["email"] == update_payload["email"]
    assert verify_password(update_payload["password"], current_user.hashed_password)


@pytest.mark.asyncio
async def test_update_user_no_permission(
    client, fake_user_service, override_get_current_user, override_user_service
):
    update_payload = {
        "username": "updateduser",
        "email": "updated@example.com",
        "password": "new_password",
    }
    other_user = fake_user_service.add_user(make_user())
    response = await client.patch(f"/users/{other_user.uuid}", json=update_payload)
    assert response.status_code == 403


@pytest.mark.asyncio
async def test_get_public_user_success(client, fake_user_service, override_user_service):
    target_user = make_user()
    fake_user_service.add_user(target_user)
    response = await client.get(f"/users/{target_user.uuid}")
    assert response.status_code == 200
    data = response.json()
    assert data["username"] == target_user.username
    assert data["email"] == target_user.email


@pytest.mark.asyncio
async def test_get_public_user_not_found(client, override_user_service):
    missing_uuid = uuid4()
    response = await client.get(f"/users/{missing_uuid}")
    assert response.status_code == status.HTTP_404_NOT_FOUND


@pytest.mark.asyncio
async def test_get_me_success(client, current_user, override_get_current_user):
    response = await client.get("/users/me")

    assert response.status_code == 200
    data = response.json()
    assert data["username"] == current_user.username
    assert data["email"] == current_user.email


@pytest.mark.asyncio
async def test_get_me_unauthorized(client):
    response = await client.get("/users/me")
    assert response.status_code == status.HTTP_401_UNAUTHORIZED


@pytest.mark.asyncio
async def test_delete_user_success(
    client,
    current_user,
    fake_user_service,
    override_get_current_user,
    override_user_service,
):
    response = await client.delete(f"/users/{current_user.uuid}")

    assert response.status_code == status.HTTP_204_NO_CONTENT
    assert current_user.uuid not in fake_user_service.users


@pytest.mark.asyncio
async def test_delete_user_no_permission(
    client,
    fake_user_service,
    override_user_service,
    override_get_current_user,
):
    other_user = fake_user_service.add_user(make_user())

    response = await client.delete(f"/users/{other_user.uuid}")

    assert response.status_code == status.HTTP_403_FORBIDDEN
