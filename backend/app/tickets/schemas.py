
from datetime import datetime

from pydantic import BaseModel, ConfigDict, computed_field
import uuid

from app.tickets.models import (
    TicketStatus, 
    TicketPriority,
    TicketCategory,
)
from app.users.schemas import UserOut




class TicketOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    
    uuid: uuid.UUID
    subject: str
    description: str
    status: TicketStatus
    priority: TicketPriority
    category: TicketCategory
    created_at: datetime
    first_response_due_at: datetime | None
    resolve_due_at: datetime | None
    first_responded_at: datetime | None
    resolved_at: datetime | None
    closed_at: datetime | None
    customer: UserOut
    support_agent: UserOut | None

class TicketCreate(BaseModel):
    subject: str
    description: str
    priority: TicketPriority = TicketPriority.MEDIUM
    category: TicketCategory = TicketCategory.GENERAL

class TicketFilter(BaseModel):
    status: list[TicketStatus] | None = None
    priority: list[TicketPriority] | None = None
    category: list[TicketCategory] | None = None
    customer_id: int | None = None
    assigned_to_id: int | None = None
    created_from: datetime | None = None
    created_to: datetime | None = None
    search: str | None = None

class ShortTicketOut(BaseModel):
    uuid: uuid.UUID
    subject: str
    description: str
    status: TicketStatus

class MessageOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    uuid: uuid.UUID
    author: UserOut
    body: str
    created_at: datetime
    updated_at: datetime

class MessageCreate(BaseModel):
    body: str

class TicketStatusUpdate(BaseModel):
    status: TicketStatus
    comment: str | None = None