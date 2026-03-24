



from datetime import datetime

from fastapi import Depends, Query
from redis.asyncio import Redis

from app.service import UnitOfWork
from app.deps import get_redis, get_uow
from app.tickets.service import MessageService, TicketService
from app.tickets.models import TicketCategory, TicketPriority, TicketStatus
from app.tickets.schemas import TicketFilter


def get_ticket_service(
    uow: UnitOfWork = Depends(get_uow),
    redis: Redis = Depends(get_redis),
) -> TicketService:
    return TicketService(uow, redis)

def get_message_service(
    uow: UnitOfWork = Depends(get_uow),
    redis: Redis = Depends(get_redis),
) -> MessageService:
    return MessageService(uow, redis)

def get_ticket_filter(
    status: list[TicketStatus] | None = Query(default=None),
    priority: list[TicketPriority] | None = Query(default=None),
    category: list[TicketCategory] | None = Query(default=None),
    customer_id: int | None = Query(default=None),
    assigned_to_id: int | None = Query(default=None),
    created_from: datetime | None = Query(default=None),
    created_to: datetime | None = Query(default=None),
    search: str | None = Query(default=None),
) -> TicketFilter:
    return TicketFilter(
        status=status,
        priority=priority,
        category=category,
        customer_id=customer_id,
        assigned_to_id=assigned_to_id,
        created_from=created_from,
        created_to=created_to,
        search=search,
    )