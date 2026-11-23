from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest

from parking_reservation.domain.outbox import (
    RETRY_CAP_SECONDS,
    OutboxEvent,
    retry_at,
    retry_delay,
    topic_for,
)


@pytest.mark.parametrize(
    ("event_type", "topic"),
    [
        ("reserved", "reservation-reserved-v1"),
        ("checked_in", "reservation-checked-in-v1"),
        ("completed", "reservation-completed-v1"),
        ("cancelled", "reservation-cancelled-v1"),
    ],
)
def test_each_event_type_has_its_topic(event_type: str, topic: str) -> None:
    assert topic_for(event_type) == topic


@pytest.mark.parametrize(
    ("attempts", "seconds"),
    [(1, 60), (2, 120), (3, 240), (4, 480), (5, 900), (6, 900), (50, 900)],
)
def test_the_backoff_doubles_and_is_capped_at_fifteen_minutes(attempts: int, seconds: int) -> None:
    assert retry_delay(attempts) == timedelta(seconds=seconds)
    assert retry_delay(attempts) <= timedelta(seconds=RETRY_CAP_SECONDS)


def test_the_next_attempt_counts_the_failure_that_just_happened() -> None:
    now = datetime(2026, 3, 1, 12, tzinfo=UTC)
    fresh = OutboxEvent(1, uuid4(), "completed", {}, 0)
    third = OutboxEvent(1, uuid4(), "completed", {}, 2)
    assert retry_at(now, fresh) == now + timedelta(seconds=60)
    assert retry_at(now, third) == now + timedelta(seconds=240)
