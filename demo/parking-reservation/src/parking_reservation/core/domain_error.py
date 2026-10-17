from parking_reservation.core.error_code import ErrorCode


class DomainError(Exception):
    """An expected business outcome; carries the code the boundary maps to a response."""

    def __init__(self, code: ErrorCode, message: str) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
