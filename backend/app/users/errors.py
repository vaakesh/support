class UserNotFoundError(Exception):
    def __init__(self, message: str = "User not found"):
        super().__init__(message)


class UserAlreadyExistsError(Exception):
    def __init__(self, message: str = "Username or email is already in use"):
        super().__init__(message)
