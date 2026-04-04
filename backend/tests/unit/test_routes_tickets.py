

import logging
import uuid

from fastapi import FastAPI
from httpx import AsyncClient
import pytest
import pytest_asyncio

from app.tickets.deps import get_ticket_service
from app.tickets.models import TicketCategory, TicketPriority, TicketStatus
from app.tickets.schemas import TicketFilter, TicketSchema
from app.users.models import UserRole
from app.users.schemas import UserSchema
from app.utils import utcnow

logger = logging.getLogger(__name__)


class FakeTicketService:
    def __init__(self, tickets: list[TicketSchema]):
        logger.debug("CREATED TICKET SERVICE")
        self._tickets = tickets

    async def get_tickets_filtered(self, filter: TicketFilter) -> list[TicketSchema]:
        logger.debug("get_tickets_filtered called")
        return self._tickets # сам фильтр не реализовываем, для юнит теста достаточно

@pytest.fixture
def fake_ticket_service():
    return FakeTicketService([])

@pytest.fixture
def override_ticket_service(app: FastAPI, fake_ticket_service):
    app.dependency_overrides[get_ticket_service] = lambda: fake_ticket_service
    yield
    app.dependency_overrides.pop(get_ticket_service, None)


def make_user_schema(**overrides) -> UserSchema:
    defaults = dict(
        id=1,
        uuid=uuid.uuid4(),
        username="testuser1",
        role=UserRole.CUSTOMER,
        email="test1@example.com",
        created_at=utcnow(),
        updated_at=utcnow(),
        is_admin=False,
        is_active=True,
    )
    return UserSchema(**{**defaults, **overrides})

def make_ticket_schema(**overrides) -> TicketSchema:
    default = dict(
        id=1,
        uuid=uuid.uuid4(),
        subject="Test subject",
        description="Test description",
        status=TicketStatus.OPEN,
        priority=TicketPriority.MEDIUM,
        category=TicketCategory.TECHNICAL,
        customer_id=1,
        assigned_to_id=None,
        resolve_due_at=None,
        created_at=utcnow(),
        updated_at=utcnow(),
        first_response_due_at=None,
        first_responded_at=None,
        resolved_at=None,
        closed_at=None,
        customer=make_user_schema(),
        support_agent=None,
    )
    return TicketSchema(**{**default, **overrides})

class TestGetTicketsFiltered:
    @pytest.mark.asyncio
    async def test_returns_empty_list(self, client: AsyncClient, override_ticket_service):
        response = await client.get("/tickets")

        assert response.status_code == 200
        assert response.json() == []

    @pytest.mark.asyncio
    async def test_returns_single_ticket(self, client: AsyncClient, override_ticket_service, fake_ticket_service: FakeTicketService):
        ticket = make_ticket_schema(support_agent=make_user_schema(id=2, username="testuser2", email="test2@example.com"))
        fake_ticket_service._tickets = [ticket]

        response = await client.get("/tickets")

        assert response.status_code == 200
        data = response.json()
        print(data)
        assert len(data) == 1
        assert data[0]["uuid"] == str(ticket.uuid)
        assert data[0]["subject"] == ticket.subject
        assert data[0]["status"] == ticket.status.value