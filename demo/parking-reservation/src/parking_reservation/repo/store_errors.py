"""One translation of database failures into StoreUnavailableError, for reads and writes."""

from collections.abc import Iterator
from contextlib import contextmanager

import psycopg

from parking_reservation.domain.ports import StoreUnavailableError


@contextmanager
def store_errors() -> Iterator[None]:
    """Turn a dropped connection, a timeout or a full pool into StoreUnavailableError."""
    try:
        yield
    except psycopg.OperationalError as err:
        raise StoreUnavailableError("the database is unavailable") from err
