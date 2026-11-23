"""The one bounded retry the service allows, on read paths only (I3)."""

from collections.abc import Callable

import psycopg
from psycopg_pool import PoolTimeout

from parking_reservation.repo.store_errors import store_errors

_NOT_TRANSIENT = (psycopg.errors.QueryCanceled, psycopg.errors.LockNotAvailable, PoolTimeout)


def read_with_retry[T](read: Callable[[], T]) -> T:
    """Run an idempotent read; repeat it once after a dropped connection.

    A timeout or a full pool is load, not a dropped connection, and is not repeated.
    Never wrap a write in this: a retried write could apply twice.
    """
    with store_errors():
        try:
            return read()
        except psycopg.OperationalError as first:
            if isinstance(first, _NOT_TRANSIENT):
                raise
            return read()
