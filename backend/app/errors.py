class TooManyRequestsError(Exception):
    def __init__(self, message: str = "Too many requests, try later."):
        super().__init__(message)