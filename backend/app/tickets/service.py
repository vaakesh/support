



import json
from uuid import UUID

from fastapi import HTTPException
from redis.asyncio import Redis

from app.service import UnitOfWork
from app.tickets.models import Ticket, TicketMessage, TicketStatus
from app.tickets.errors import InvalidStatusTransitionError, TicketNotAssignedError, TicketNotFoundError
from app.tickets.schemas import MessageCreate, TicketCreate, TicketFilter, TicketOut, TicketSchema
from app.tickets.utils import ALLOWED_TRANSITIONS, calculate_first_response_due_at, calculate_resolve_due_at
from app.utils import utcnow
from sqlalchemy.exc import IntegrityError

from app.users.errors import PermissionDeniedError, UserNotFoundError
from app.users.models import User
from app.tickets.ws import ConnectionManager
from app.users.schemas import UserOut

class ChatService:
    def __init__(self, message_service: MessageService, connection_manager: ConnectionManager):
        self.message_service = message_service
        self.connection_manager = connection_manager

    async def handle_incoming_message(
            self,
            ticket_uuid: UUID,
            user: User,
            data: dict,
    ) -> None:
        message = await self.message_service.send_message(
            MessageCreate(body=data["message"]),
            ticket_uuid,
            user.id,
        )
        payload = {
            **data,
            "author": UserOut.model_validate(user).model_dump(mode="json"),
            "message_uuid": str(message.uuid),
            "body": message.body,
            "created_at": str(message.created_at),
            "updated_at": str(message.updated_at),
        }
        await self.connection_manager.broadcast(ticket_uuid, payload)
        

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
            return ticket
    
    async def get_all_messages_by_ticket(self, ticket_uuid: UUID, current_user_id: int, before: UUID, limit: int | None) -> tuple[list[TicketMessage], bool]:
        async with self.uow as uow:
            ticket = await self._get_ticket_by_uuid(uow, ticket_uuid, current_user_id)
            messages, has_more = await uow.message_repo.get_all_messages_by_ticket(ticket.id, before, limit)
            return messages, has_more
    
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
    
    async def check_ticket_access(self, ticket_uuid: UUID, user: User) -> None:
        async with self.uow as uow:
            ticket = await self._get_by_uuid(uow, ticket_uuid)
            
            if user.id != ticket.customer_id and user.id != ticket.assigned_to_id:
                raise PermissionDeniedError()

    async def change_status(self, ticket_uuid: UUID, new_status: TicketStatus, current_user: User) -> TicketSchema:
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
            await uow.ticket_repo.refresh(ticket)
            cache_key = f"ticket:{ticket_uuid}"
            await self.redis.delete(cache_key)
            return TicketSchema.model_validate(ticket)
            
    async def get_by_uuid(self, ticket_uuid: UUID) -> TicketSchema:
        async with self.uow as uow:
            cache_key = f"ticket:{ticket_uuid}"
            cached = await self.redis.get(cache_key)
            if cached:
                return TicketSchema.model_validate_json(cached)
            
            ticket = await self._get_by_uuid(uow, ticket_uuid)

            ticket_schema = TicketSchema.model_validate(ticket)
            await self.redis.setex(
                cache_key,
                300,
                ticket_schema.model_dump_json(),
            )
            return ticket_schema
        
    async def get_all(self, limit: int = 200) -> list[TicketSchema]:
        async with self.uow as uow:
            tickets = await uow.ticket_repo.get_all(limit)
            return [TicketSchema.model_validate(ticket) for ticket in tickets]
        
    async def create_ticket(self, payload: TicketCreate, current_user_id: int) -> TicketSchema:
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

                created_ticket = await uow.ticket_repo.get_by_uuid(ticket.uuid)

                return TicketSchema.model_validate(created_ticket)
        except IntegrityError:
            raise

    async def get_tickets_filtered(self, filter: TicketFilter) -> list[TicketSchema]:
        async with self.uow as uow:
            tickets = await uow.ticket_repo.get_tickets_filtered(filter)
            return [TicketSchema.model_validate(ticket) for ticket in tickets]
        
    async def assign_ticket(self, ticket_uuid: UUID, support_agent_id: int) -> TicketSchema:
        try:
            async with self.uow as uow:
                is_updated = await uow.ticket_repo.assign_ticket(ticket_uuid, support_agent_id)
                if is_updated:
                    ticket = await self._get_by_uuid(uow, ticket_uuid)
                    await uow.commit()
                    await uow.ticket_repo.refresh(ticket)
                    cache_key = f"ticket:{ticket_uuid}"
                    await self.redis.delete(cache_key)
                    return TicketSchema.model_validate(ticket)
                else:
                    raise TicketNotFoundError()
        except IntegrityError:
            raise UserNotFoundError("Support agent not found")

    async def mark_viewed(self, ticket_uuid: UUID) -> TicketSchema:
        async with self.uow as uow:
            ticket = await self._get_by_uuid_for_update(uow, ticket_uuid)

            if ticket.status == TicketStatus.NEW:
                ticket.status = TicketStatus.OPEN

            await uow.commit()
            await uow.ticket_repo.refresh(ticket)
            cache_key = f"ticket:{ticket_uuid}"
            await self.redis.delete(cache_key)
            return TicketSchema.model_validate(ticket)

    async def _get_by_uuid(self, uow: UnitOfWork, ticket_uuid: UUID) -> Ticket:
        ticket = await uow.ticket_repo.get_by_uuid(ticket_uuid)
        if ticket is None:
            raise TicketNotFoundError(f"Ticket with uuid={ticket_uuid} not found")
        return ticket
    
    async def _get_by_uuid_for_update(self, uow: UnitOfWork, ticket_uuid: UUID) -> Ticket:
        ticket = await uow.ticket_repo.get_by_uuid_for_update(ticket_uuid)
        if ticket is None:
            raise TicketNotFoundError(f"Ticket with uuid={ticket_uuid} not found")
        return ticket
    
