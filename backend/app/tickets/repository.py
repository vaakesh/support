



from uuid import UUID

from sqlalchemy import or_, select, update

from app.repository import AbstractRepository
from app.tickets.models import Ticket, TicketMessage
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from sqlalchemy.exc import IntegrityError
from app.users.schemas import UserCreate
from app.tickets.schemas import TicketFilter

class MessageRepository(AbstractRepository[TicketMessage]):
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    def add(self, message: TicketMessage) -> None:
        self.session.add(message)
    async def refresh(self, *args, **kwargs) -> None:
        await self.session.refresh(*args, **kwargs)
    async def delete(self, message: TicketMessage) -> None:
        await self.session.delete(message)
    async def get_by_id(self, message_id: int) -> TicketMessage:
        await self.session.get(TicketMessage, message_id)
    
    async def get_all_messages_by_ticket(self, ticket_id: int) -> list[TicketMessage]:
        stmt = (
            select(TicketMessage)
            .where(TicketMessage.ticket_id == ticket_id)
            .options(
                selectinload(TicketMessage.author),
            )
            .order_by(TicketMessage.created_at)
        )
        return (await self.session.execute(stmt)).scalars().all()

class TicketRepository(AbstractRepository[Ticket]):
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
    
    async def get_by_id(self, ticket_id: int) -> Ticket:
        return await self.session.get(Ticket, ticket_id)
    def add(self, ticket: Ticket) -> None:
        self.session.add(ticket)
    async def refresh(self, ticket: Ticket) -> None:
        self.session.refresh(ticket)
    async def delete(self, ticket: Ticket) -> None:
        self.session.delete(ticket)

    async def get_by_uuid(self, ticket_uuid: UUID) -> Ticket | None:
        stmt = (
            select(Ticket)
            .where(Ticket.uuid == ticket_uuid)
            .options(
                selectinload(Ticket.customer),
                selectinload(Ticket.support_agent),
            )
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()
    
    async def get_by_uuid_for_update(self, ticket_uuid: UUID) -> Ticket | None:
        stmt = (
            select(Ticket)
            .where(Ticket.uuid == ticket_uuid)
            .options(
                selectinload(Ticket.customer),
                selectinload(Ticket.support_agent),
            )
            .with_for_update()
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()
    
    async def get_all(self, limit: int = 200) -> list[Ticket]:
        stmt = (
            select(Ticket)
            .options(
                selectinload(Ticket.customer),
                selectinload(Ticket.support_agent),
            )
            .order_by(Ticket.created_at.desc())
            .limit(limit)
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())
    
    def _build_tickets_filters(self, filter: TicketFilter) -> list:
        conditions = []

        if filter.status:
            conditions.append(Ticket.status.in_(filter.status))
        if filter.priority:
            conditions.append(Ticket.priority.in_(filter.priority))
        if filter.category:
            conditions.append(Ticket.category.in_(filter.category))
        if filter.customer_id is not None:
            conditions.append(Ticket.customer_id == filter.customer_id)
        if filter.assigned_to_id is not None:
            conditions.append(Ticket.assigned_to_id == filter.assigned_to_id)
        if filter.created_from is not None:
            conditions.append(Ticket.created_at >= filter.created_from)
        if filter.created_to is not None:
            conditions.append(Ticket.created_at <= filter.created_to)
        if filter.search:
            search_value = f"%{filter.search}%"
            stmt = stmt.where(
                or_(
                    Ticket.title.ilike(search_value),
                    Ticket.description.ilike(search_value),
                )
            )
        return conditions


    async def get_tickets_filtered(self, filter: TicketFilter) -> list[Ticket]:
        stmt = (
            select(Ticket)
            .options(
                selectinload(Ticket.customer),
                selectinload(Ticket.support_agent),
            )
        )
        conditions = self._build_tickets_filters(filter)
        if conditions:
            stmt = stmt.where(*conditions)

        stmt = stmt.order_by(Ticket.created_at.desc()).limit(200)

        result = await self.session.execute(stmt)
        return result.scalars().all()
    
    async def assign_ticket(self, ticket_uuid: UUID, support_agent_id: int):
        stmt = (
            update(Ticket)
            .where(
                Ticket.uuid == ticket_uuid
            )
            .values(assigned_to_id=support_agent_id)
        )
        result = await self.session.execute(stmt)
        return bool(result.rowcount)