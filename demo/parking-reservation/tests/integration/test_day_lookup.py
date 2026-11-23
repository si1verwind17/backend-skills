"""AP3: a garage's reservations for a garage-local date."""

from collections.abc import Callable
from datetime import UTC, date, datetime
from uuid import uuid4

from parking_reservation.repo.database import Pool
from parking_reservation.repo.reservation_repo import ReservationRepo
from tests.support import NOW


def book(repo, garage, start, end, driver="d1"):  # type: ignore[no-untyped-def]
    row = repo.book(
        public_id=uuid4(),
        event_id=uuid4(),
        driver_id=driver,
        idempotency_key=str(uuid4()),
        garage_id=garage,
        window_start=start,
        window_end=end,
        now=NOW,
    )
    assert row
    return row


def utc(*args: int) -> datetime:
    return datetime(*args, tzinfo=UTC)


def test_an_unknown_garage_is_none_and_an_empty_one_is_an_empty_list(
    pool: Pool, seed_garage: Callable[..., int]
) -> None:
    repo = ReservationRepo(pool)
    garage = seed_garage(1)
    assert repo.list_for_garage_day(garage + 1, date(2026, 3, 2)) is None
    assert repo.list_for_garage_day(garage, date(2026, 3, 2)) == []


def test_reservations_overlapping_the_day_are_listed_in_window_order(
    pool: Pool, seed_garage: Callable[..., int]
) -> None:
    repo = ReservationRepo(pool)
    garage = seed_garage(3)
    late = book(repo, garage, utc(2026, 3, 2, 18), utc(2026, 3, 2, 20))
    overnight = book(repo, garage, utc(2026, 3, 1, 22), utc(2026, 3, 2, 2))
    early = book(repo, garage, utc(2026, 3, 2, 8), utc(2026, 3, 2, 9))
    listed = repo.list_for_garage_day(garage, date(2026, 3, 2))
    assert listed is not None
    assert [r.public_id for r in listed] == [overnight.public_id, early.public_id, late.public_id]


def test_touching_the_day_boundary_does_not_count(
    pool: Pool, seed_garage: Callable[..., int]
) -> None:
    repo = ReservationRepo(pool)
    garage = seed_garage(3)
    ends_at_start = book(repo, garage, utc(2026, 3, 1, 22), utc(2026, 3, 2, 0))
    starts_at_next = book(repo, garage, utc(2026, 3, 3, 0), utc(2026, 3, 3, 2))
    inside = book(repo, garage, utc(2026, 3, 2, 23), utc(2026, 3, 3, 1))
    listed = repo.list_for_garage_day(garage, date(2026, 3, 2))
    assert listed is not None
    ids = {r.public_id for r in listed}
    assert ids == {inside.public_id}
    assert ends_at_start.public_id not in ids and starts_at_next.public_id not in ids


def test_the_day_is_the_garages_own_calendar_day_across_a_clock_change(
    pool: Pool, seed_garage: Callable[..., int]
) -> None:
    repo = ReservationRepo(pool)
    # Berlin: 2026-03-29 starts at 2026-03-28T23:00Z and ends at 2026-03-29T22:00Z (23 hours).
    garage = seed_garage(4, timezone="Europe/Berlin")
    before = book(repo, garage, utc(2026, 3, 28, 21), utc(2026, 3, 28, 23))
    first = book(repo, garage, utc(2026, 3, 28, 22), utc(2026, 3, 28, 23, 30))
    last = book(repo, garage, utc(2026, 3, 29, 21, 30), utc(2026, 3, 29, 23))
    after = book(repo, garage, utc(2026, 3, 29, 22), utc(2026, 3, 29, 23))
    listed = repo.list_for_garage_day(garage, date(2026, 3, 29))
    assert listed is not None
    ids = {r.public_id for r in listed}
    assert ids == {first.public_id, last.public_id}
    assert before.public_id not in ids and after.public_id not in ids


def test_every_status_is_listed(pool: Pool, seed_garage: Callable[..., int]) -> None:
    repo = ReservationRepo(pool)
    garage = seed_garage(1)
    row = book(repo, garage, utc(2026, 3, 2, 8), utc(2026, 3, 2, 9))
    repo.cancel(row.public_id, "d1", uuid4(), NOW)
    listed = repo.list_for_garage_day(garage, date(2026, 3, 2))
    assert listed is not None and [r.status.value for r in listed] == ["cancelled"]


def test_other_garages_are_not_listed(pool: Pool, seed_garage: Callable[..., int]) -> None:
    repo = ReservationRepo(pool)
    one, two = seed_garage(1), seed_garage(1, name="other")
    book(repo, two, utc(2026, 3, 2, 8), utc(2026, 3, 2, 9))
    assert repo.list_for_garage_day(one, date(2026, 3, 2)) == []
