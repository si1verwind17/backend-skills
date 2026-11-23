"""Tier 3: the booking path against a real Postgres."""

import threading
from collections.abc import Callable
from datetime import timedelta
from uuid import uuid4

import psycopg
import pytest
from psycopg.rows import dict_row
from psycopg_pool import ConnectionPool

from parking_reservation.domain.ports import StoreUnavailableError
from parking_reservation.domain.status import Status
from parking_reservation.repo.database import Pool
from parking_reservation.repo.garage_repo import GarageRepo
from parking_reservation.repo.reservation_repo import ReservationRepo
from tests.support import NOW

HOUR = timedelta(hours=1)


def book(repo: ReservationRepo, garage: int, start, end, driver="d1", key=None):  # type: ignore[no-untyped-def]
    return repo.book(
        public_id=uuid4(),
        event_id=uuid4(),
        driver_id=driver,
        idempotency_key=key or str(uuid4()),
        garage_id=garage,
        window_start=start,
        window_end=end,
        now=NOW,
    )


def test_the_lowest_free_spot_is_booked_first(pool: Pool, seed_garage: Callable[..., int]) -> None:
    garage = seed_garage(2)
    repo = ReservationRepo(pool)
    first = book(repo, garage, NOW + HOUR, NOW + 2 * HOUR)
    second = book(repo, garage, NOW + HOUR, NOW + 2 * HOUR)
    assert first and second and first.spot_id < second.spot_id
    assert first.status is Status.BOOKED and first.driver_id == "d1"


def test_a_full_garage_creates_no_row(pool: Pool, seed_garage: Callable[..., int]) -> None:
    garage = seed_garage(1)
    repo = ReservationRepo(pool)
    assert book(repo, garage, NOW + HOUR, NOW + 2 * HOUR)
    assert book(repo, garage, NOW + 90 * timedelta(minutes=1), NOW + 3 * HOUR) is None


def test_touching_windows_do_not_overlap(pool: Pool, seed_garage: Callable[..., int]) -> None:
    garage = seed_garage(1)
    repo = ReservationRepo(pool)
    first = book(repo, garage, NOW + HOUR, NOW + 2 * HOUR)
    after = book(repo, garage, NOW + 2 * HOUR, NOW + 3 * HOUR)
    before = book(repo, garage, NOW, NOW + HOUR)
    assert first and after and before
    assert {first.spot_id, after.spot_id, before.spot_id} == {first.spot_id}


def test_inactive_spots_are_never_assigned(pool: Pool, seed_garage: Callable[..., int]) -> None:
    garage = seed_garage(1)
    with pool.connection() as conn:
        conn.execute("UPDATE spot SET active = false")
    assert book(ReservationRepo(pool), garage, NOW + HOUR, NOW + 2 * HOUR) is None


def test_a_repeated_key_inserts_nothing_and_is_found_by_key(
    pool: Pool, seed_garage: Callable[..., int]
) -> None:
    garage = seed_garage(2)
    repo = ReservationRepo(pool)
    first = book(repo, garage, NOW + HOUR, NOW + 2 * HOUR, key="same")
    again = book(repo, garage, NOW + HOUR, NOW + 2 * HOUR, key="same")
    assert first and again is None
    assert repo.find_by_key("d1", "same") == first
    assert repo.find_by_key("d2", "same") is None


def test_each_booking_writes_its_event_atomically(
    pool: Pool, seed_garage: Callable[..., int]
) -> None:
    garage = seed_garage(1)
    booking = book(ReservationRepo(pool), garage, NOW + HOUR, NOW + 2 * HOUR)
    assert booking
    with pool.connection() as conn:
        rows = conn.execute("SELECT event_type, status, attempts, payload FROM outbox").fetchall()
    assert len(rows) == 1
    event = rows[0]
    assert (event["event_type"], event["status"], event["attempts"]) == ("reserved", "pending", 0)
    payload = event["payload"]
    assert payload["reservation_id"] == str(booking.public_id)
    assert payload["driver_id"] == "d1" and payload["garage_id"] == garage
    assert payload["window_start"] == "2026-03-01T13:00:00+00:00"
    assert payload["occurred_at"] == "2026-03-01T12:00:00+00:00"
    assert payload["checked_in_at"] is None and payload["event_type"] == "reserved"


def test_concurrent_requests_for_the_last_spot_book_exactly_one(
    pool: Pool, seed_garage: Callable[..., int]
) -> None:
    garage = seed_garage(1)
    repo = ReservationRepo(pool)
    results: list[object] = []
    barrier = threading.Barrier(4)

    def attempt() -> None:
        barrier.wait()
        results.append(book(repo, garage, NOW + HOUR, NOW + 2 * HOUR))

    threads = [threading.Thread(target=attempt) for _ in range(4)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    assert len([r for r in results if r]) == 1 and len(results) == 4


def test_concurrent_requests_with_free_spots_all_succeed_on_distinct_spots(
    pool: Pool, seed_garage: Callable[..., int]
) -> None:
    garage = seed_garage(4)
    repo = ReservationRepo(pool)
    results: list[object] = []
    barrier = threading.Barrier(4)

    def attempt() -> None:
        barrier.wait()
        results.append(book(repo, garage, NOW + HOUR, NOW + 2 * HOUR))

    threads = [threading.Thread(target=attempt) for _ in range(4)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    assert all(results) and len({r.spot_id for r in results}) == 4  # type: ignore[attr-defined]


def test_concurrent_twins_with_one_key_create_one_reservation(
    pool: Pool, seed_garage: Callable[..., int]
) -> None:
    garage = seed_garage(3)
    repo = ReservationRepo(pool)
    results: list[object] = []
    barrier = threading.Barrier(3)

    def attempt() -> None:
        barrier.wait()
        results.append(book(repo, garage, NOW + HOUR, NOW + 2 * HOUR, key="twin"))

    threads = [threading.Thread(target=attempt) for _ in range(3)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    assert len([r for r in results if r]) == 1
    with pool.connection() as conn:
        assert conn.execute("SELECT count(*) AS n FROM reservation").fetchone()["n"] == 1  # type: ignore[index]


def test_the_database_itself_refuses_a_double_booking(
    pool: Pool, seed_garage: Callable[..., int]
) -> None:
    garage = seed_garage(1)
    assert book(ReservationRepo(pool), garage, NOW + HOUR, NOW + 2 * HOUR)
    with pytest.raises(psycopg.errors.ExclusionViolation), pool.connection() as conn:
        conn.execute(
            "INSERT INTO reservation (public_id, garage_id, spot_id, driver_id, idempotency_key,"
            " window_start, window_end, status, updated_at)"
            " SELECT gen_random_uuid(), garage_id, spot_id, 'x', 'x2', %s, %s, 'booked', now()"
            " FROM spot",
            (NOW + HOUR + timedelta(minutes=30), NOW + 3 * HOUR),
        )


def test_a_cancelled_or_completed_reservation_releases_its_spot(
    pool: Pool, seed_garage: Callable[..., int]
) -> None:
    garage = seed_garage(1)
    repo = ReservationRepo(pool)
    assert book(repo, garage, NOW + HOUR, NOW + 2 * HOUR)
    with pool.connection() as conn:
        conn.execute("UPDATE reservation SET status = 'cancelled', cancelled_at = now()")
    assert book(repo, garage, NOW + HOUR, NOW + 2 * HOUR)


def test_get_for_driver_hides_other_drivers(pool: Pool, seed_garage: Callable[..., int]) -> None:
    garage = seed_garage(1)
    repo = ReservationRepo(pool)
    mine = book(repo, garage, NOW + HOUR, NOW + 2 * HOUR)
    assert mine
    assert repo.get_for_driver(mine.public_id, "d1") == mine
    assert repo.get_for_driver(mine.public_id, "d2") is None
    assert repo.get_for_driver(uuid4(), "d1") is None


def test_garage_exists(pool: Pool, seed_garage: Callable[..., int]) -> None:
    garage = seed_garage(0)
    repo = GarageRepo(pool)
    assert repo.exists(garage) and not repo.exists(garage + 1)


def test_a_lock_that_cannot_be_taken_in_time_is_unavailability(
    database_url: str, seed_garage: Callable[..., int]
) -> None:
    garage = seed_garage(1)
    short_pool = ConnectionPool(
        database_url,
        min_size=1,
        max_size=1,
        kwargs={"options": "-c lock_timeout=200", "row_factory": dict_row},
        open=True,
    )
    try:
        with psycopg.connect(database_url) as holder:
            holder.execute("SELECT pg_advisory_xact_lock(1, %s::int)", (garage,))
            with pytest.raises(StoreUnavailableError):
                book(ReservationRepo(short_pool), garage, NOW + HOUR, NOW + 2 * HOUR)  # type: ignore[arg-type]
    finally:
        short_pool.close()
