from parking_reservation.core.error_code import ErrorCode

# Architecture design, API inventory: one status per business code.
STATUS_BY_CODE: dict[ErrorCode, int] = {
    ErrorCode.INVALID_REQUEST: 422,
    ErrorCode.INVALID_WINDOW: 422,
    ErrorCode.IDEMPOTENCY_KEY_REUSED: 409,
    ErrorCode.GARAGE_NOT_FOUND: 404,
    ErrorCode.RESERVATION_NOT_FOUND: 404,
    ErrorCode.NO_SPOT_AVAILABLE: 409,
    ErrorCode.INVALID_TRANSITION: 409,
    ErrorCode.CHECKIN_WINDOW_CLOSED: 409,
    ErrorCode.UNAUTHENTICATED: 401,
    ErrorCode.FORBIDDEN: 403,
    ErrorCode.UNAVAILABLE: 503,
    ErrorCode.INTERNAL_ERROR: 500,
}
