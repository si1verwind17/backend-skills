"""Outbox events and what the relay decides for each: pure data and rules (W5)."""

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any
from uuid import UUID

RETRY_BASE_SECONDS = 30
RETRY_CAP_SECONDS = 15 * 60
ALERT_AFTER_ATTEMPTS = 10


@dataclass(frozen=True)
class OutboxEvent:
    outbox_id: int
    event_id: UUID
    event_type: str
    payload: dict[str, Any]
    attempts: int


@dataclass(frozen=True)
class Published:
    """The broker accepted the event."""


@dataclass(frozen=True)
class RetryLater:
    """A transient failure: keep the row pending and try again at `next_attempt_at`."""

    error: str
    next_attempt_at: datetime


@dataclass(frozen=True)
class Parked:
    """The broker rejected this one event as invalid or oversize: stop trying."""

    error: str


Settlement = Published | RetryLater | Parked


@dataclass(frozen=True)
class Settled:
    event: OutboxEvent
    settlement: Settlement


@dataclass
class SweepResult:
    """What one sweep did. `failure` is set when the store gave out part-way."""

    published: int = 0
    retried: int = 0
    parked: list[tuple[UUID, str]] = field(default_factory=list)
    stuck: list[UUID] = field(default_factory=list)
    failure: Exception | None = None


def topic_for(event_type: str) -> str:
    """The topic of an event type: `reservation-<type>-v1` (AD8)."""
    return f"reservation-{event_type.replace('_', '-')}-v1"


def retry_delay(failed_attempts: int) -> timedelta:
    """Backoff once `failed_attempts` attempts have failed: 30 s x 2^n, capped at 15 min."""
    seconds = min(RETRY_BASE_SECONDS * 2**failed_attempts, RETRY_CAP_SECONDS)
    return timedelta(seconds=seconds)


def retry_at(now: datetime, event: OutboxEvent) -> datetime:
    """When to try `event` again after the attempt that just failed."""
    return now + retry_delay(event.attempts + 1)
