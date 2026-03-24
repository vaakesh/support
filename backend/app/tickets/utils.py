


from datetime import datetime, timedelta

from app.tickets.models import TicketPriority, TicketStatus

FIRST_RESPONSE_SLA = {
    TicketPriority.LOW: timedelta(hours=24),
    TicketPriority.MEDIUM: timedelta(hours=8),
    TicketPriority.HIGH: timedelta(hours=2),
    TicketPriority.CRITICAL: timedelta(minutes=30),
}

RESOLVE_SLA = {
    TicketPriority.LOW: timedelta(days=5),
    TicketPriority.MEDIUM: timedelta(days=3),
    TicketPriority.HIGH: timedelta(days=1),
    TicketPriority.CRITICAL: timedelta(hours=4),
}

ALLOWED_TRANSITIONS = {
    TicketStatus.NEW: [TicketStatus.OPEN],
    TicketStatus.OPEN: [TicketStatus.IN_PROGRESS, TicketStatus.CLOSED],
    TicketStatus.IN_PROGRESS: [TicketStatus.PENDING, TicketStatus.RESOLVED, TicketStatus.CLOSED],
    TicketStatus.PENDING: [TicketStatus.IN_PROGRESS, TicketStatus.CLOSED],
    TicketStatus.RESOLVED: [TicketStatus.CLOSED, TicketStatus.OPEN],
    TicketStatus.CLOSED: [TicketStatus.OPEN],
}

# не учитываем рабочие часы/выходные для простоты
def calculate_first_response_due_at(priority: TicketPriority, created_at: datetime) -> datetime:
    return created_at + FIRST_RESPONSE_SLA[priority]

def calculate_resolve_due_at(priority: TicketPriority, created_at: datetime) -> datetime:
    return created_at + RESOLVE_SLA[priority]

