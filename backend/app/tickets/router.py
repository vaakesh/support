



from uuid import UUID

from fastapi import APIRouter, Depends, Query, Request, WebSocket, WebSocketDisconnect
from sqlalchemy import select

from app.tickets.schemas import MessageCreate, MessageOut, TicketCreate, TicketFilter, TicketOut, TicketStatusUpdate
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.deps import get_session
from app.tickets.models import Ticket
from app.auth.deps import get_current_user, get_current_user_ws
from app.users.models import User
from app.tickets.service import ChatService, MessageService, TicketService
from app.tickets.deps import get_chat_service, get_message_service, get_ticket_filter, get_ticket_service
from app.tickets.ws import ConnectionManager, get_connection_manager
from app.users.schemas import UserOut

router = APIRouter(prefix="/tickets")

@router.websocket("/{ticket_uuid}/ws")
async def ticket_chat_ws(
    ticket_uuid: UUID,
    ws: WebSocket,
    current_user: User = Depends(get_current_user_ws),
    connection_manager: ConnectionManager = Depends(get_connection_manager),
    message_service: MessageService = Depends(get_message_service),
    chat_service: ChatService = Depends(get_chat_service),
    ticket_service: TicketService = Depends(get_ticket_service),
):
    await ticket_service.check_ticket_access(ticket_uuid, current_user)

    key = str(ticket_uuid)
    user_uuid = str(current_user.uuid)
    await connection_manager.connect(key, ws, user_uuid)

    try:
        while True:
            data = await ws.receive_json() # получаем сообщение
            await chat_service.handle_incoming_message(ticket_uuid, current_user, data)
    except WebSocketDisconnect:
        connection_manager.disconnect(key, ws, user_uuid)

@router.get("", response_model=list[TicketOut])
async def get_tickets_filtered(
    filter: TicketFilter = Depends(get_ticket_filter),
    ticket_service: TicketService = Depends(get_ticket_service),
):
    return await ticket_service.get_tickets_filtered(filter)

@router.get("/all", response_model=list[TicketOut])
async def get_all_tickets(
    ticket_service: TicketService = Depends(get_ticket_service),
) -> list[TicketOut]:
    tickets = await ticket_service.get_all()
    return tickets

@router.get("/{ticket_uuid}", response_model=TicketOut)
async def get_ticket(
    ticket_uuid: UUID,
    ticket_service: TicketService = Depends(get_ticket_service),
) -> TicketOut:
    ticket = await ticket_service.get_by_uuid(ticket_uuid)
    return ticket

@router.get("/{ticket_uuid}/view", response_model=TicketOut)
async def view_ticket(
    ticket_uuid: UUID,
    ticket_service: TicketService = Depends(get_ticket_service),
) -> TicketOut:
    ticket = await ticket_service.mark_viewed(ticket_uuid)
    return ticket

@router.patch("/{ticket_uuid}/status", response_model=TicketOut)
async def update_ticket_status(
    ticket_uuid: UUID,
    payload: TicketStatusUpdate,
    current_user: User = Depends(get_current_user),
    ticket_service: TicketService = Depends(get_ticket_service),
):
    ticket = await ticket_service.change_status(ticket_uuid, payload.status, current_user)
    return ticket

@router.get("/{ticket_uuid}/messages")
async def get_messages_by_ticket(
    ticket_uuid: UUID,
    before: UUID | None = Query(default=None),
    limit: int = Query(default=20, le=50),
    current_user: User = Depends(get_current_user),
    message_service: MessageService = Depends(get_message_service),
):
    messages, has_more = await message_service.get_all_messages_by_ticket(ticket_uuid, current_user.id, before, limit)
    return {
        "messages": [MessageOut.model_validate(message) for message in messages],
        "has_more": has_more,
    }

@router.post("/{ticket_uuid}/messages", response_model=MessageOut)
async def send_message(
    ticket_uuid: UUID,
    payload: MessageCreate,
    current_user: User = Depends(get_current_user),
    message_service: MessageService = Depends(get_message_service),
):
    message = await message_service.send_message(payload, ticket_uuid, current_user.id)
    return message


@router.post("/", response_model=TicketOut)
async def create_ticket(
    payload: TicketCreate,
    current_user: User = Depends(get_current_user),
    ticket_service: TicketService = Depends(get_ticket_service),
):
    ticket = await ticket_service.create_ticket(payload, current_user.id)
    return ticket

@router.patch("/assign/{ticket_uuid}", response_model=TicketOut)
async def assign_ticket_to_support_agent(
    ticket_uuid: UUID,
    support_agent_id: int,
    ticket_service: TicketService = Depends(get_ticket_service),
):
    ticket = await ticket_service.assign_ticket(ticket_uuid, support_agent_id)
    return ticket