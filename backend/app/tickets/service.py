



import json
from uuid import UUID

from redis import Redis

from app.service import UnitOfWork
from app.tickets.models import Ticket, TicketMessage, TicketStatus
from app.tickets.errors import InvalidStatusTransitionError, TicketNotAssignedError, TicketNotFoundError
from app.tickets.schemas import MessageCreate, TicketCreate, TicketFilter, TicketOut
from app.tickets.utils import ALLOWED_TRANSITIONS, calculate_first_response_due_at, calculate_resolve_due_at
from app.utils import utcnow
from sqlalchemy.exc import IntegrityError

from app.users.errors import PermissionDeniedError
from app.users.models import User

class MessageService:
    def __init__(self, uow: UnitOfWork, redis: Redis) -> None:
        self.uow = uow
        self.redis = redis
    
    async def _get_ticket_by_uuid(self, uow: UnitOfWork, ticket_uuid: UUID, current_user_id: int) -> Ticket:
            ticket = await uow.ticket_repo.get_by_uuid(ticket_uuid)
            if ticket is None:
                raise TicketNotFoundError(f"Ticket with uuid={ticket_uuid} not found")
            if ticket.customer_id != current_user_id and ticket.assigned_to_id != current_user_id:
                raise PermissionDeniedError()
    
    async def get_all_messages_by_ticket(self, ticket_uuid: UUID, current_user_id: int) -> list[TicketMessage]:
        async with self.uow as uow:
            ticket = await self._get_ticket_by_uuid(uow, ticket_uuid, current_user_id)
            messages = await uow.message_repo.get_all_messages_by_ticket(ticket.id)
            return messages
    
    async def send_message(self, payload: MessageCreate, ticket_uuid: UUID, current_user_id: int) -> TicketMessage:
        async with self.uow as uow:
            ticket = await self._get_ticket_by_uuid(uow, ticket_uuid, current_user_id)
            new_message = TicketMessage(
                ticket_id=ticket.id,
                author_id=current_user_id,
                **payload.model_dump(),
            )
            uow.message_repo.add(new_message)
            await uow.commit()
            await uow.message_repo.refresh(new_message, attribute_names=["author"])
            return new_message


class TicketService:
    def __init__(self, uow: UnitOfWork, redis: Redis) -> None:
        self.uow = uow
        self.redis = redis
    
    async def change_status(self, ticket_uuid: UUID, new_status: TicketStatus, current_user: User) -> Ticket:
        async with self.uow as uow:
            ticket = await self._get_by_uuid_for_update(uow, ticket_uuid)
            if ticket.support_agent is None:
                raise TicketNotAssignedError()
            if ticket.support_agent.id != current_user.id:
                raise PermissionDeniedError()
            
            if new_status not in ALLOWED_TRANSITIONS[ticket.status]:
                raise InvalidStatusTransitionError(message=f"Invalid status transition from {ticket.status} \
                                                    to {new_status} for ticket={ticket_uuid}")

            now = utcnow()
            if new_status == TicketStatus.RESOLVED:
                ticket.resolved_at = now
            elif new_status == TicketStatus.CLOSED:
                ticket.closed_at = now

            ticket.status = new_status
            await uow.commit()
            cache_key = f"ticket:{ticket_uuid}"
            await self.redis.setex(cache_key, 300, TicketOut.model_validate(ticket).model_dump_json())
            return ticket
            
            


    async def get_by_uuid(self, ticket_uuid: UUID) -> Ticket:
        async with self.uow as uow:
            return await self._get_by_uuid(uow, ticket_uuid)
        
    async def get_all(self, limit: int = 200) -> Ticket:
        async with self.uow as uow:
            tickets = await uow.ticket_repo.get_all(limit)
            return tickets
        
    async def create_ticket(self, payload: TicketCreate, current_user_id: int) -> Ticket:
        try:
            async with self.uow as uow:
                now = utcnow()
                ticket = Ticket(
                    subject=payload.subject,
                    description=payload.description,
                    priority=payload.priority,
                    category=payload.category,
                    customer_id=current_user_id,
                    first_response_due_at=calculate_first_response_due_at(payload.priority, now),
                    resolve_due_at=calculate_resolve_due_at(payload.priority, now),
                )
                uow.ticket_repo.add(ticket)
                await uow.commit()
                await uow.ticket_repo.refresh(ticket)

                created_ticket = await uow.ticket_repo.get_by_uuid(ticket.uuid)

                return created_ticket
        except IntegrityError:
            raise

    async def get_tickets_filtered(self, filter: TicketFilter) -> list[Ticket]:
        async with self.uow as uow:
            tickets = await uow.ticket_repo.get_tickets_filtered(filter)
            return tickets
        
    async def assign_ticket(self, ticket_uuid: UUID, support_agent_id: int):
        try:
            async with self.uow as uow:
                is_updated = await uow.ticket_repo.assign_ticket(ticket_uuid, support_agent_id) # пофиксить non-existent ticket_uuid, support_agent_id, ...
                if is_updated:
                    ticket = await self._get_by_uuid(uow, ticket_uuid)
                    await uow.commit()
                    await self.redis.delete(f"ticket:{ticket_uuid}")
                    return ticket
        except IntegrityError: # разделить ошибки
            raise

    async def mark_viewed(self, ticket_uuid: UUID) -> Ticket:
        async with self.uow as uow:
            ticket = await self._get_by_uuid_for_update(uow, ticket_uuid)

            if ticket.status == TicketStatus.NEW:
                ticket.status = TicketStatus.OPEN

            await uow.commit()
            await self.redis.delete(f"ticket:{ticket_uuid}")
            return ticket

    async def _get_by_uuid(self, uow: UnitOfWork, ticket_uuid: UUID) -> Ticket:
        cache_key = f"ticket:{ticket_uuid}"
        cached = await self.redis.get(cache_key)
        if cached:
            return TicketOut.model_validate_json(cached)
        
        ticket = await uow.ticket_repo.get_by_uuid(ticket_uuid)
        if ticket is None:
            raise TicketNotFoundError(f"Ticket with uuid={ticket_uuid} not found")
        ticket_json = TicketOut.model_validate(ticket).model_dump_json()
        await self.redis.setex(
            cache_key,
            300,
            ticket_json,
        )
        return ticket
    
    async def _get_by_uuid_for_update(self, uow: UnitOfWork, ticket_uuid: UUID) -> Ticket:
        ticket = await uow.ticket_repo.get_by_uuid_for_update(ticket_uuid)
        if ticket is None:
            raise TicketNotFoundError(f"Ticket with uuid={ticket_uuid} not found")
        return ticket
    
