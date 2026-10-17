"""Driver notifications: domain types and the pure scheduling rules.

Reminders are written to notification_outbox ahead of time by the
scheduling run and sent by the dispatch run once their send_after time
has passed — the same outbox pattern billing uses, so a Pub/Sub outage
delays reminders instead of losing them.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import StrEnum
from uuid import UUID

from app.domain.models import ReservationStatus, TimeWindow


class NotificationKind(StrEnum):
    RESERVATION_REMINDER = "reservation_reminder"


class SkipReason(StrEnum):
    RESERVATION_NOT_ACTIVE = "reservation_not_active"
    WINDOW_ALREADY_STARTED = "window_already_started"
    DRIVER_OPTED_OUT = "driver_opted_out"
    NO_CONTACT = "no_contact"


@dataclass(frozen=True, slots=True)
class ReminderPolicy:
    lead: timedelta
    horizon: timedelta


@dataclass(frozen=True, slots=True)
class NotificationRow:
    """A due notification_outbox row as claimed by one dispatch run,
    joined with the reservation and driver state it depends on."""

    notification_id: int
    kind: NotificationKind
    reservation_id: int
    reservation_public_id: UUID
    reservation_status: ReservationStatus
    driver_id: int
    garage_id: int
    garage_name: str
    window: TimeWindow
    send_after: datetime
    attempt_count: int
    driver_email: str | None
    driver_phone: str | None
    notify_reminders: bool | None


@dataclass(frozen=True, slots=True)
class ReminderMessage:
    """Payload published to `driver-notification-v1`."""

    notification_id: int
    kind: NotificationKind
    driver_id: int
    reservation_id: UUID
    garage_id: int
    garage_name: str
    window: TimeWindow
    email: str | None
    phone: str | None


def reminder_send_after(window_start: datetime, policy: ReminderPolicy) -> datetime:
    return window_start - policy.lead


def scheduling_range(now: datetime, policy: ReminderPolicy) -> TimeWindow:
    """Reservations whose window starts inside this range get a reminder
    row on this run. The range starts at `now`, so a reservation booked
    less than `lead` before its start still gets one, sent immediately."""
    return TimeWindow(start=now, end=now + policy.horizon)


def skip_reason(row: NotificationRow, now: datetime) -> SkipReason | None:
    """Why a due reminder should not be sent any more, or None to send it.
    State can change between scheduling and dispatch: the reservation may
    have been cancelled, or the driver may have turned reminders off."""
    if row.reservation_status != ReservationStatus.RESERVED:
        return SkipReason.RESERVATION_NOT_ACTIVE
    if row.window.start <= now:
        return SkipReason.WINDOW_ALREADY_STARTED
    if row.notify_reminders is False:
        return SkipReason.DRIVER_OPTED_OUT
    if row.notify_reminders is None or (row.driver_email is None and row.driver_phone is None):
        # No account yet (reservation predates accounts): nowhere to send.
        return SkipReason.NO_CONTACT
    return None


def to_reminder_message(row: NotificationRow) -> ReminderMessage:
    return ReminderMessage(
        notification_id=row.notification_id,
        kind=row.kind,
        driver_id=row.driver_id,
        reservation_id=row.reservation_public_id,
        garage_id=row.garage_id,
        garage_name=row.garage_name,
        window=row.window,
        email=row.driver_email,
        phone=row.driver_phone,
    )
