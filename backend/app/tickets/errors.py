class TicketNotFoundError(Exception):
    def __init__(self, message: str = "Ticket not found"):
        super().__init__(message)

class InvalidStatusTransitionError(Exception):
    def __init__(self, message: str = "Invalid status transition"):
        super().__init__(message)

class TicketNotAssignedError(Exception):
    def __init__(self, message: str = "Ticket not assigned"):
        super().__init__(message)