import logging
import time
from collections.abc import Awaitable, Callable

from fastapi import FastAPI, Request, Response
from fastapi.responses import JSONResponse

from parking_reservation.api.error_status import STATUS_BY_CODE
from parking_reservation.api.schemas.error_response import ErrorResponse
from parking_reservation.core.error_code import ErrorCode

_log = logging.getLogger("parking_reservation.request")


def _level_for(status: int, warn: bool) -> int:
    if status >= 500:
        return logging.ERROR
    if status in (401, 403) or warn:
        return logging.WARNING
    return logging.INFO


def install_request_logging(app: FastAPI) -> None:
    """Exactly one log line per request outcome, and the one place a defect is logged and answered.

    Handlers answer expected failures; anything that still escapes is a defect: it is logged here once
    with its traceback and answered as INTERNAL_ERROR, so nothing is re-raised for a second logger.
    The service must run with the server access log off for the same reason (the container command, slice 3).
    """

    @app.middleware("http")
    async def log_request(request: Request, call_next: Callable[[Request], Awaitable[Response]]) -> Response:
        started = time.perf_counter()
        try:
            response = await call_next(request)
        except Exception:
            request.state.error_code = ErrorCode.INTERNAL_ERROR.value
            _log.error("request failed", exc_info=True, extra={"fields": _fields(request, 500, started)})
            body = ErrorResponse(code=ErrorCode.INTERNAL_ERROR.value, message="internal error")
            return JSONResponse(
                status_code=STATUS_BY_CODE[ErrorCode.INTERNAL_ERROR], content=body.model_dump()
            )
        fields = _fields(request, response.status_code, started)
        _log.log(
            _level_for(response.status_code, getattr(request.state, "warn", False)),
            "request",
            extra={"fields": fields},
        )
        return response


def _fields(request: Request, status: int, started: float) -> dict[str, object]:
    route = request.scope.get("route")
    state = request.state
    fields: dict[str, object] = {
        "method": request.method,
        "route": getattr(route, "path", request.url.path),
        "status": status,
        "error_code": getattr(state, "error_code", None),
        "duration_ms": round((time.perf_counter() - started) * 1000, 1),
    }
    optional = {
        "trace": request.headers.get("x-cloud-trace-context"),
        "reservation_id": getattr(state, "reservation_id", None),
        "garage_code": getattr(state, "garage_code", None),
        "database_error": getattr(state, "database_error", None),
    }
    fields.update({key: value for key, value in optional.items() if value is not None})
    fields["relay"] = getattr(state, "extra_fields", None)
    if fields["relay"] is None:
        del fields["relay"]
    return fields
