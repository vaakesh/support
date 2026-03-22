from datetime import datetime
import enum
from typing import TYPE_CHECKING
import uuid

from sqlalchemy import UUID, DateTime, Enum, ForeignKey, func

from app.database import Base
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.types import BIGINT, VARCHAR, Text


if TYPE_CHECKING:
    from app.tickets.models import Ticket
    from backend.app.auth.models import UserSession
    from app.users.models import User


class TicketStatus(str, enum.Enum):
    NEW = "new"
    OPEN = "open"
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    RESOLVED = "resolved"
    CLOSED = "closed"

class TicketPriority(str, enum.Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"

class TicketCategory(str, enum.Enum):
    TECHNICAL = "technical"
    GENERAL = "general"


class Ticket(Base):
    __tablename__ = "tickets"

    id: Mapped[int] = mapped_column(BIGINT, primary_key=True, autoincrement=True)
    uuid: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        default=uuid.uuid4,
        unique=True,
        nullable=False,
        index=True,
    )
    subject: Mapped[str] = mapped_column(VARCHAR(255), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)

    status: Mapped[TicketStatus] = mapped_column(
        Enum(TicketStatus),
        nullable=False,
        default=TicketStatus.NEW,
        index=True,
    )
    priority: Mapped[TicketPriority] = mapped_column(
        Enum(TicketPriority),
        nullable=False,
        default=TicketPriority.MEDIUM,
        index=True,
    )
    category: Mapped[TicketCategory] = mapped_column(
        Enum(TicketCategory), 
        nullable=False, 
        default=TicketCategory.GENERAL,
    )

    customer_id: Mapped[int] = mapped_column(
        BIGINT,
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    assigned_to_id: Mapped[int | None] = mapped_column(
        BIGINT,
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    
    first_response_due_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    resolve_due_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    first_responded_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    resolved_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    closed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    customer: Mapped["User"] = relationship(
        "User",
        foreign_keys=[customer_id],
        back_populates="created_tickets",
    )

    support_agent: Mapped["User | None"] = relationship(
        "User",
        foreign_keys=[assigned_to_id],
        back_populates="assigned_tickets",
    )

    messages: Mapped[list["TicketMessage"]] = relationship(
        "TicketMessage",
        foreign_keys="TicketMessage.ticket_id",
        back_populates="ticket"
    )

class TicketMessage(Base):
    __tablename__ = "ticket_messages"

    id: Mapped[int] = mapped_column(BIGINT, primary_key=True, autoincrement=True)
    uuid: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        default=uuid.uuid4,
        unique=True,
        nullable=False,
        index=True,
    )

    ticket_id: Mapped[int] = mapped_column(BIGINT, ForeignKey("tickets.id", ondelete="CASCADE"))
    author_id: Mapped[int] = mapped_column(BIGINT, ForeignKey("users.id", ondelete=""))

    body: Mapped[str] = mapped_column(Text, nullable=False)
    
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    ) 

    ticket: Mapped["Ticket"] = relationship("Ticket", foreign_keys=[ticket_id], back_populates="messages")
    author: Mapped["User"] = relationship("User", foreign_keys=[author_id], back_populates="messages")