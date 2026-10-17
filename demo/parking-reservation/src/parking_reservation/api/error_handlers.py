from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from psycopg import Error as DatabaseError
from starlette.exceptions import HTTPException as HttpError

from parking_reservation.api.error_status import STATUS_BY_CODE
from parking_reservation.api.schemas.error_response import ErrorResponse
from parking_reservation.core.domain_error import DomainError
from parking_reservation.core.error_code import ErrorCode


def _respond(request: Request, code: ErrorCode, message: str) -> JSONResponse:
    request.state.error_code = code.value
    return JSONResponse(
        status_code=STATUS_BY_CODE[code], content=ErrorResponse(code=code.value, message=message).model_dump()
    )


def install_error_handlers(app: FastAPI) -> None:
    """The one exhaustive mapping from errors to responses; request_logging records the outcome."""

    @app.exception_handler(DomainError)
    def handle_domain_error(request: Request, error: DomainError) -> JSONResponse:
        return _respond(request, error.code, error.message)

    @app.exception_handler(RequestValidationError)
    def handle_validation_error(request: Request, error: RequestValidationError) -> JSONResponse:
        first = error.errors()[0]
        location = ".".join(str(part) for part in first["loc"])
        return _respond(request, ErrorCode.INVALID_REQUEST, f"{location}: {first['msg']}")

    @app.exception_handler(DatabaseError)
    def handle_database_error(request: Request, error: DatabaseError) -> JSONResponse:
        # I3: any database failure is a retryable 503; the log line says which kind it was, so a
        # SQL or schema bug is not mistaken for an outage.
        request.state.database_error = f"{type(error).__name__} {error.sqlstate or ''}".strip()
        return _respond(request, ErrorCode.UNAVAILABLE, "temporarily unavailable, retry")

    @app.exception_handler(HttpError)
    def handle_http_error(request: Request, error: HttpError) -> JSONResponse:
        request.state.error_code = f"HTTP_{error.status_code}"
        body = ErrorResponse(code=f"HTTP_{error.status_code}", message=str(error.detail))
        return JSONResponse(status_code=error.status_code, content=body.model_dump())
