"""One log line per request outcome, owned by this layer alone."""

import logging
from collections.abc import Awaitable, Callable

from fastapi import Request, Response

from parking_reservation.api.error_responses import error_response
from parking_reservation.domain.errors import ErrorCode

log = logging.getLogger("parking_reservation.api")


async def log_outcome(
    request: Request, call_next: Callable[[Request], Awaitable[Response]]
) -> Response:
    try:
        response = await call_next(request)
        failure: Exception | None = None
    except Exception as err:
        failure = err
        response = error_response(request, ErrorCode.UNAVAILABLE, "temporarily unavailable, repeat")
    level = _level(response.status_code)
    log.log(
        level,
        "outcome method=%s path=%s status=%s code=%s actor=%s garage=%s reservation=%s",
        request.method,
        request.url.path,
        response.status_code,
        getattr(request.state, "error_code", "-"),
        request.headers.get("x-actor-id", "-"),
        getattr(request.state, "garage_id", "-"),
        getattr(request.state, "reservation_id", "-"),
        exc_info=failure,
    )
    return response


def _level(status: int) -> int:
    if status >= 500:
        return logging.ERROR
    return logging.WARNING if status >= 400 else logging.INFO
