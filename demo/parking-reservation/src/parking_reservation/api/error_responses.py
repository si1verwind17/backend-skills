"""The one place that maps outcomes to HTTP responses and records them."""

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from parking_reservation.api.models import ErrorBody
from parking_reservation.domain.errors import DomainError, ErrorCode
from parking_reservation.domain.ports import StoreUnavailableError

_STATUS = {
    ErrorCode.INVALID_WINDOW: 422,
    ErrorCode.INVALID_REQUEST: 400,
    ErrorCode.GARAGE_NOT_FOUND: 404,
    ErrorCode.NOT_FOUND: 404,
    ErrorCode.GARAGE_FULL: 409,
    ErrorCode.IDEMPOTENCY_KEY_REUSED: 409,
    ErrorCode.ILLEGAL_TRANSITION: 409,
    ErrorCode.OUTSIDE_WINDOW: 409,
    ErrorCode.FORBIDDEN: 403,
    ErrorCode.UNAUTHENTICATED: 401,
    ErrorCode.UNAVAILABLE: 503,
}


def error_response(request: Request, code: ErrorCode, message: str) -> JSONResponse:
    """Build the JSON error and note its code for the outcome log."""
    request.state.error_code = code.value
    body = ErrorBody(code=code.value, message=message)
    return JSONResponse(status_code=_STATUS[code], content=body.model_dump())


def install_error_handlers(app: FastAPI) -> None:
    @app.exception_handler(DomainError)
    async def _domain(request: Request, err: DomainError) -> JSONResponse:
        return error_response(request, err.code, err.message)

    @app.exception_handler(RequestValidationError)
    async def _invalid(request: Request, err: RequestValidationError) -> JSONResponse:
        fields = ", ".join(".".join(str(part) for part in e["loc"]) for e in err.errors())
        return error_response(request, ErrorCode.INVALID_REQUEST, f"invalid request: {fields}")

    @app.exception_handler(StoreUnavailableError)
    async def _unavailable(request: Request, err: StoreUnavailableError) -> JSONResponse:
        return error_response(request, ErrorCode.UNAVAILABLE, "temporarily unavailable, repeat")
