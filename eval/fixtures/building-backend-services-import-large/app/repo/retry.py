"""One bounded, shared retry helper for the single in-process retry this
service needs: Postgres can report a deadlock between two transactions
concurrently inserting rows that both need to check the same GiST
exclusion constraint (excl_reservation_spot_active_window) in opposite
orders — a well-documented Postgres behavior, not a bug in the query.
Retrying is safe here because the insert never committed (backend-code-
conventions: never retry a non-idempotent operation — this one simply
didn't happen yet)."""

from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable
from typing import TypeVar

from psycopg.errors import DeadlockDetected

T = TypeVar("T")

_MAX_ATTEMPTS = 3
_BACKOFF_SECONDS = 0.05


async def retry_on_deadlock(operation: Callable[[], Awaitable[T]]) -> T:
    last_error: DeadlockDetected | None = None
    for attempt in range(_MAX_ATTEMPTS):
        try:
            return await operation()
        except DeadlockDetected as exc:
            last_error = exc
            if attempt < _MAX_ATTEMPTS - 1:
                await asyncio.sleep(_BACKOFF_SECONDS * (attempt + 1))
    assert last_error is not None
    raise last_error
