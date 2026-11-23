"""The closed set of business outcomes a caller can be given."""

from enum import StrEnum


class ErrorCode(StrEnum):
    INVALID_WINDOW = "INVALID_WINDOW"
    INVALID_REQUEST = "INVALID_REQUEST"
    GARAGE_NOT_FOUND = "GARAGE_NOT_FOUND"
    GARAGE_FULL = "GARAGE_FULL"
    IDEMPOTENCY_KEY_REUSED = "IDEMPOTENCY_KEY_REUSED"
    ILLEGAL_TRANSITION = "ILLEGAL_TRANSITION"
    OUTSIDE_WINDOW = "OUTSIDE_WINDOW"
    NOT_FOUND = "NOT_FOUND"
    FORBIDDEN = "FORBIDDEN"
    UNAUTHENTICATED = "UNAUTHENTICATED"
    UNAVAILABLE = "UNAVAILABLE"


class DomainError(Exception):
    """An expected outcome that is answered to the caller, never a defect."""

    def __init__(self, code: ErrorCode, message: str) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
