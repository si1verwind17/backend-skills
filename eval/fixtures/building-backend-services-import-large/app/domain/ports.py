"""Structural prerequisites: injected clock and id generation.

Per backend-code-conventions, no inline now()/random() anywhere business
data is created — both are swappable ports so tests are deterministic and
services never reach for wall-clock time or randomness directly.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Protocol


class Clock(Protocol):
    def now(self) -> datetime: ...


class SystemClock:
    def now(self) -> datetime:
        return datetime.now(UTC)


class FixedClock:
    """Test double: always returns the same instant unless advanced."""

    def __init__(self, fixed: datetime) -> None:
        self._fixed = fixed

    def now(self) -> datetime:
        return self._fixed

    def advance(self, delta) -> None:
        self._fixed = self._fixed + delta


class IdGenerator(Protocol):
    def new_reservation_public_id(self) -> uuid.UUID: ...

    def new_quote_public_id(self) -> uuid.UUID: ...


class Uuid7IdGenerator:
    """Production id generator: time-ordered UUIDv7 (stdlib, Python 3.14+)."""

    def new_reservation_public_id(self) -> uuid.UUID:
        return uuid.uuid7()

    def new_quote_public_id(self) -> uuid.UUID:
        return uuid.uuid7()


class SequentialIdGenerator:
    """Test double: deterministic, strictly increasing UUIDs derived from a
    counter, so assertions can pin exact ids."""

    def __init__(self, start: int = 1) -> None:
        self._next = start

    def new_reservation_public_id(self) -> uuid.UUID:
        return self._take()

    def new_quote_public_id(self) -> uuid.UUID:
        return self._take()

    def _take(self) -> uuid.UUID:
        value = self._next
        self._next += 1
        return uuid.UUID(int=value)
