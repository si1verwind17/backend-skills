"""Reminder scheduling rules — pure, no I/O."""

from dataclasses import replace
from datetime import UTC, datetime, timedelta
from uuid import UUID

from app.domain.models import ReservationStatus, TimeWindow
from app.domain.notifications import (
    NotificationKind,
    NotificationRow,
    ReminderPolicy,
    SkipReason,
    reminder_send_after,
    scheduling_range,
    skip_reason,
    to_reminder_message,
)

NOW = datetime(2026, 8, 15, 12, tzinfo=UTC)
POLICY = ReminderPolicy(lead=timedelta(minutes=60), horizon=timedelta(hours=24))


def _row(**overrides) -> NotificationRow:
    fields = {
        "notification_id": 1,
        "kind": NotificationKind.RESERVATION_REMINDER,
        "reservation_id": 10,
        "reservation_public_id": UUID(int=10),
        "reservation_status": ReservationStatus.RESERVED,
        "driver_id": 42,
        "garage_id": 3,
        "garage_name": "Centraal",
        "window": TimeWindow(start=NOW + timedelta(minutes=30), end=NOW + timedelta(hours=2)),
        "send_after": NOW - timedelta(minutes=30),
        "attempt_count": 0,
        "driver_email": "jane@example.com",
        "driver_phone": None,
        "notify_reminders": True,
    }
    fields.update(overrides)
    return NotificationRow(**fields)


def test_reminder_send_after_is_lead_before_start() -> None:
    assert reminder_send_after(NOW, POLICY) == NOW - timedelta(minutes=60)


def test_scheduling_range_starts_now() -> None:
    assert scheduling_range(NOW, POLICY) == TimeWindow(start=NOW, end=NOW + timedelta(hours=24))


def test_an_active_reservation_with_contact_is_sent() -> None:
    assert skip_reason(_row(), NOW) is None


def test_cancelled_reservation_is_skipped() -> None:
    assert skip_reason(_row(reservation_status=ReservationStatus.CANCELLED), NOW) == SkipReason.RESERVATION_NOT_ACTIVE


def test_checked_in_reservation_is_skipped() -> None:
    assert skip_reason(_row(reservation_status=ReservationStatus.CHECKED_IN), NOW) == SkipReason.RESERVATION_NOT_ACTIVE


def test_started_window_is_skipped() -> None:
    row = _row(window=TimeWindow(start=NOW - timedelta(minutes=1), end=NOW + timedelta(hours=1)))

    assert skip_reason(row, NOW) == SkipReason.WINDOW_ALREADY_STARTED


def test_opted_out_driver_is_skipped() -> None:
    assert skip_reason(_row(notify_reminders=False), NOW) == SkipReason.DRIVER_OPTED_OUT


def test_driver_without_account_is_skipped() -> None:
    row = _row(notify_reminders=None, driver_email=None, driver_phone=None)

    assert skip_reason(row, NOW) == SkipReason.NO_CONTACT


def test_phone_only_driver_is_sent() -> None:
    assert skip_reason(_row(driver_email=None, driver_phone="+31612345678"), NOW) is None


def test_to_reminder_message_carries_public_id_and_contact() -> None:
    row = _row()

    message = to_reminder_message(row)

    assert message.reservation_id == UUID(int=10)
    assert message.email == "jane@example.com"
    assert message.garage_name == "Centraal"
    assert message.window == row.window


def test_to_reminder_message_never_exposes_internal_reservation_id() -> None:
    message = to_reminder_message(replace(_row(), reservation_id=999))

    assert message.reservation_id == UUID(int=10)
