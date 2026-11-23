"""W2-W4 against a real Postgres: guards, atomic events and spot release."""

import threading
from collections.abc import Callable
from datetime import timedelta
from uuid import uuid4

from parking_reservation.domain.reservation import Reservation
from parking_reservation.domain.status import Status
from parking_reservation.repo.database import Pool
from parking_reservation.repo.reservation_repo import ReservationRepo
from tests.support import NOW

HOUR = timedelta(hours=1)


def book(
    repo: ReservationRepo, garage: int, start=NOW - HOUR, end=NOW + HOUR, driver="d1"
) -> Reservation:  # type: ignore[no-untyped-def]
    booked = repo.book(
        public_id=uuid4(),
        event_id=uuid4(),
        driver_id=driver,
        idempotency_key=str(uuid4()),
        garage_id=garage,
        window_start=start,
        window_end=end,
        now=NOW - 2 * HOUR,
    )
    assert booked
    return booked


def events(pool: Pool) -> list[tuple[str, str]]:
    with pool.connection() as conn:
        rows = conn.execute("SELECT event_type, status FROM outbox ORDER BY outbox_id").fetchall()
    return [(r["event_type"], r["status"]) for r in rows]


def test_the_full_lifecycle_writes_one_event_per_transition(
    pool: Pool, seed_garage: Callable[..., int]
) -> None:
    repo = ReservationRepo(pool)
    row = book(repo, seed_garage(1))
    checked_in = repo.check_in(row.public_id, "d1", uuid4(), NOW)
    assert checked_in and checked_in.status is Status.CHECKED_IN and checked_in.checked_in_at == NOW
    done = repo.check_out(row.public_id, "d1", uuid4(), NOW + timedelta(minutes=30))
    assert done and done.status is Status.COMPLETED
    assert done.checked_out_at == NOW + timedelta(minutes=30) and done.checked_in_at == NOW
    assert events(pool) == [
        ("reserved", "pending"),
        ("checked_in", "pending"),
        ("completed", "pending"),
    ]


def test_the_completed_event_carries_the_billing_fields(
    pool: Pool, seed_garage: Callable[..., int]
) -> None:
    repo = ReservationRepo(pool)
    garage = seed_garage(1)
    row = book(repo, garage)
    repo.check_in(row.public_id, "d1", uuid4(), NOW)
    event_id = uuid4()
    repo.check_out(row.public_id, "d1", event_id, NOW + timedelta(minutes=30))
    with pool.connection() as conn:
        payload = conn.execute(
            "SELECT payload FROM outbox WHERE event_type = 'completed'"
        ).fetchone()["payload"]  # type: ignore[index]
    assert payload == {
        "event_id": str(event_id),
        "event_type": "completed",
        "occurred_at": "2026-03-01T12:30:00+00:00",
        "reservation_id": str(row.public_id),
        "driver_id": "d1",
        "garage_id": garage,
        "spot_id": row.spot_id,
        "window_start": "2026-03-01T11:00:00+00:00",
        "window_end": "2026-03-01T13:00:00+00:00",
        "checked_in_at": "2026-03-01T12:00:00+00:00",
        "checked_out_at": "2026-03-01T12:30:00+00:00",
        "cancelled_at": None,
    }


def test_check_out_is_never_stamped_before_check_in(
    pool: Pool, seed_garage: Callable[..., int]
) -> None:
    repo = ReservationRepo(pool)
    row = book(repo, seed_garage(1))
    repo.check_in(row.public_id, "d1", uuid4(), NOW)
    done = repo.check_out(row.public_id, "d1", uuid4(), NOW - timedelta(seconds=5))
    assert done and done.checked_out_at == NOW
    with pool.connection() as conn:
        occurred = conn.execute(
            "SELECT payload ->> 'occurred_at' AS at FROM outbox WHERE event_type = 'completed'"
        ).fetchone()["at"]  # type: ignore[index]
    assert occurred == "2026-03-01T12:00:00+00:00"


def test_a_repeated_check_out_matches_no_row_and_adds_no_event(
    pool: Pool, seed_garage: Callable[..., int]
) -> None:
    repo = ReservationRepo(pool)
    row = book(repo, seed_garage(1))
    repo.check_in(row.public_id, "d1", uuid4(), NOW)
    assert repo.check_out(row.public_id, "d1", uuid4(), NOW)
    assert repo.check_out(row.public_id, "d1", uuid4(), NOW) is None
    assert [e for e, _ in events(pool)].count("completed") == 1


def test_concurrent_check_outs_complete_once(pool: Pool, seed_garage: Callable[..., int]) -> None:
    repo = ReservationRepo(pool)
    row = book(repo, seed_garage(1))
    repo.check_in(row.public_id, "d1", uuid4(), NOW)
    results: list[object] = []
    barrier = threading.Barrier(4)

    def attempt() -> None:
        barrier.wait()
        results.append(repo.check_out(row.public_id, "d1", uuid4(), NOW))

    threads = [threading.Thread(target=attempt) for _ in range(4)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    assert len([r for r in results if r]) == 1
    assert [e for e, _ in events(pool)].count("completed") == 1


def test_another_driver_changes_nothing(pool: Pool, seed_garage: Callable[..., int]) -> None:
    repo = ReservationRepo(pool)
    row = book(repo, seed_garage(1))
    assert repo.check_in(row.public_id, "intruder", uuid4(), NOW) is None
    assert repo.cancel(row.public_id, "intruder", uuid4(), NOW) is None
    assert repo.get_for_driver(row.public_id, "d1") == row


def test_check_in_is_only_possible_inside_the_window(
    pool: Pool, seed_garage: Callable[..., int]
) -> None:
    repo = ReservationRepo(pool)
    garage = seed_garage(2)
    early = book(repo, garage, NOW + HOUR, NOW + 2 * HOUR)
    ended = book(repo, garage, NOW - 2 * HOUR, NOW)
    assert repo.check_in(early.public_id, "d1", uuid4(), NOW) is None
    assert repo.check_in(ended.public_id, "d1", uuid4(), NOW) is None
    assert repo.check_in(early.public_id, "d1", uuid4(), NOW + HOUR)


def test_a_checked_in_reservation_cannot_be_cancelled(
    pool: Pool, seed_garage: Callable[..., int]
) -> None:
    repo = ReservationRepo(pool)
    row = book(repo, seed_garage(1))
    repo.check_in(row.public_id, "d1", uuid4(), NOW)
    assert repo.cancel(row.public_id, "d1", uuid4(), NOW) is None


def test_a_booked_reservation_cannot_be_checked_out(
    pool: Pool, seed_garage: Callable[..., int]
) -> None:
    repo = ReservationRepo(pool)
    row = book(repo, seed_garage(1))
    assert repo.check_out(row.public_id, "d1", uuid4(), NOW) is None


def test_cancel_and_completion_release_the_spot(
    pool: Pool, seed_garage: Callable[..., int]
) -> None:
    repo = ReservationRepo(pool)
    garage = seed_garage(1)
    first = book(repo, garage)
    assert repo.cancel(first.public_id, "d1", uuid4(), NOW)
    second = book(repo, garage)
    repo.check_in(second.public_id, "d1", uuid4(), NOW)
    repo.check_out(second.public_id, "d1", uuid4(), NOW)
    assert book(repo, garage)
    assert [e for e, _ in events(pool)].count("cancelled") == 1
