"""Domain types for the parking-reservation service.

These are plain dataclasses used by business logic (rules, services). They
are never returned directly over the wire — the api layer maps them to/from
its own request/response schemas (see app/api/schemas.py) so a JSON field
rename never touches this module.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from uuid import UUID


class ReservationStatus(StrEnum):
    RESERVED = "reserved"
    CHECKED_IN = "checked_in"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


@dataclass(frozen=True, slots=True)
class TimeWindow:
    start: datetime
    end: datetime


@dataclass(frozen=True, slots=True)
class Reservation:
    reservation_id: int
    public_id: UUID
    garage_id: int
    spot_id: int
    driver_id: int
    status: ReservationStatus
    window: TimeWindow
    checked_in_at: datetime | None
    completed_at: datetime | None
    cancelled_at: datetime | None
    created_at: datetime
    updated_at: datetime


@dataclass(frozen=True, slots=True)
class Garage:
    garage_id: int
    name: str
    timezone: str


@dataclass(frozen=True, slots=True)
class BillingNotification:
    """The payload shape published to `reservation-completed-v1`.

    Field set matches architecture-design.md's event catalog entry
    verbatim — reservation_id here is the public (UUID) identifier, never
    the internal bigint.
    """

    reservation_id: UUID
    driver_id: int
    garage_id: int
    spot_id: int
    window: TimeWindow
    completed_at: datetime


@dataclass(frozen=True, slots=True)
class OutboxRow:
    """An unpublished (or just-attempted) billing_outbox row, as claimed by
    the publisher for one delivery attempt."""

    outbox_id: int
    reservation_id: int
    reservation_public_id: UUID
    driver_id: int
    garage_id: int
    spot_id: int
    window: TimeWindow
    completed_at: datetime
    attempt_count: int
