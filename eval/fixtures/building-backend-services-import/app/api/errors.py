"""The single boundary handler: maps every domain error (and unexpected
defects) to an HTTP response, and is the only place that logs these
outcomes (backend-code-conventions: "Every error has one owner" / "Exactly
one layer owns outcome logging"). Business/service code never logs these
itself — it only raises.
"""

from __future__ import annotations

import logging

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from app.api.schemas import ErrorResponse
from app.domain.errors import (
    GarageNotFound,
    InvalidTimeWindow,
    InvalidTransition,
    NoSpotAvailable,
    ReservationNotFound,
)

logger = logging.getLogger(__name__)

_NOT_FOUND = (ReservationNotFound, GarageNotFound)
_CONFLICT = (NoSpotAvailable, InvalidTransition)
_UNPROCESSABLE = (InvalidTimeWindow,)


async def _on_validation_error(request: Request, exc: RequestValidationError) -> JSONResponse:
    logger.info(
        "request rejected: malformed body",
        extra={"path": request.url.path, "errors": exc.errors()},
    )
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
        content=ErrorResponse(error="invalid_request", detail=str(exc)).model_dump(),
    )


async def _on_not_found(request: Request, exc: Exception) -> JSONResponse:
    logger.info("request rejected: not found", extra={"path": request.url.path, "reason": str(exc)})
    return JSONResponse(
        status_code=status.HTTP_404_NOT_FOUND,
        content=ErrorResponse(error="not_found", detail=str(exc)).model_dump(),
    )


async def _on_conflict(request: Request, exc: Exception) -> JSONResponse:
    logger.info("request rejected: conflict", extra={"path": request.url.path, "reason": str(exc)})
    return JSONResponse(
        status_code=status.HTTP_409_CONFLICT,
        content=ErrorResponse(error="conflict", detail=str(exc)).model_dump(),
    )


async def _on_unprocessable(request: Request, exc: Exception) -> JSONResponse:
    logger.info(
        "request rejected: business rule violation",
        extra={"path": request.url.path, "reason": str(exc)},
    )
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
        content=ErrorResponse(error="invalid_request", detail=str(exc)).model_dump(),
    )


async def _on_unexpected(request: Request, exc: Exception) -> JSONResponse:
    # Fail loudly: unexpected defects get one contextual log at error
    # level and a generic 500 — no attempt to recover or classify.
    logger.error(
        "unexpected error handling request",
        extra={"path": request.url.path},
        exc_info=exc,
    )
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content=ErrorResponse(error="internal_error", detail="an unexpected error occurred").model_dump(),
    )


def register_error_handlers(app: FastAPI) -> None:
    app.add_exception_handler(RequestValidationError, _on_validation_error)
    for exc_type in _NOT_FOUND:
        app.add_exception_handler(exc_type, _on_not_found)
    for exc_type in _CONFLICT:
        app.add_exception_handler(exc_type, _on_conflict)
    for exc_type in _UNPROCESSABLE:
        app.add_exception_handler(exc_type, _on_unprocessable)
    # Registered last / broadest: anything not one of the modeled domain
    # errors above is treated as an unexpected defect.
    app.add_exception_handler(Exception, _on_unexpected)
