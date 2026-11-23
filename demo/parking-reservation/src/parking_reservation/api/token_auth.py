"""Every call except GET /health carries a Google ID token from the one account allowed there."""

from collections.abc import Awaitable, Callable

from fastapi import Request, Response
from starlette.concurrency import run_in_threadpool

from parking_reservation.api.error_responses import error_response
from parking_reservation.domain.errors import ErrorCode
from parking_reservation.domain.ports import (
    TokenRejectedError,
    TokenVerifier,
    TokenVerifierUnavailableError,
)


def token_auth(
    verifier: TokenVerifier,
    audience: str,
    front_end_account: str,
    scheduler_account: str,
) -> Callable[[Request, Callable[[Request], Awaitable[Response]]], Awaitable[Response]]:
    """Build the middleware: /v1/* from the front end, /internal/* from the scheduler."""

    async def middleware(
        request: Request, call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        path = request.url.path
        if request.method == "GET" and path == "/health":
            return await call_next(request)
        token = _bearer(request.headers.get("authorization"))
        if token is None:
            return error_response(request, ErrorCode.UNAUTHENTICATED, "missing ID token")
        try:
            account = await run_in_threadpool(verifier.verify, token, audience)
        except TokenRejectedError:
            return error_response(request, ErrorCode.UNAUTHENTICATED, "invalid ID token")
        except TokenVerifierUnavailableError:
            return error_response(request, ErrorCode.UNAVAILABLE, "temporarily unavailable, repeat")
        allowed = _allowed_account(path, front_end_account, scheduler_account)
        if allowed is None or account != allowed:
            return error_response(request, ErrorCode.FORBIDDEN, "caller may not use this path")
        return await call_next(request)

    return middleware


def _bearer(header: str | None) -> str | None:
    if not header:
        return None
    scheme, _, token = header.partition(" ")
    return token.strip() if scheme.lower() == "bearer" and token.strip() else None


def _allowed_account(path: str, front_end_account: str, scheduler_account: str) -> str | None:
    if path.startswith("/v1/"):
        return front_end_account
    if path.startswith("/internal/"):
        return scheduler_account
    return None
