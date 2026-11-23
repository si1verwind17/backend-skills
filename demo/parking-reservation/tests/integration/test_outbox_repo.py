"""W5 against a real Postgres: claiming, settling, backoff, concurrency and re-drive."""

import threading
from collections.abc import Callable
from datetime import timedelta
from uuid import uuid4

import psycopg
import pytest

from parking_reservation.domain.outbox import OutboxEvent, Parked, Published, RetryLater, retry_at
from parking_reservation.repo.database import Pool
from parking_reservation.repo.outbox_repo import OutboxRepo
from parking_reservation.repo.reservation_repo import ReservationRepo
from tests.support import NOW

HOUR = timedelta(hours=1)


def reserve_n(pool: Pool, garage: int, count: int) -> None:
    repo = ReservationRepo(pool)
    for n in range(count):
        booked = repo.book(
            public_id=uuid4(),
            event_id=uuid4(),
            driver_id=f"d{n}",
            idempotency_key=f"k{n}",
            garage_id=garage,
            window_start=NOW + HOUR,
            window_end=NOW + 2 * HOUR,
            now=NOW,
        )
        assert booked


def rows(pool: Pool) -> list[dict[str, object]]:
    with pool.connection() as conn:
        return list(conn.execute("SELECT * FROM outbox ORDER BY outbox_id").fetchall())


def test_a_published_row_is_marked_and_never_claimed_again(
    pool: Pool, seed_garage: Callable[..., int]
) -> None:
    reserve_n(pool, seed_garage(1), 1)
    repo = OutboxRepo(pool)
    settled = repo.settle_next(NOW, lambda e: Published())
    assert settled and settled.event.event_type == "reserved"
    row = rows(pool)[0]
    assert row["status"] == "published" and row["published_at"] == NOW and row["attempts"] == 0
    assert repo.settle_next(NOW, lambda e: Published()) is None


def test_a_transient_failure_backs_off_and_the_row_stays_pending(
    pool: Pool, seed_garage: Callable[..., int]
) -> None:
    reserve_n(pool, seed_garage(1), 1)
    repo = OutboxRepo(pool)
    repo.settle_next(NOW, lambda e: RetryLater("broker down", retry_at(NOW, e)))
    row = rows(pool)[0]
    assert (
        row["status"] == "pending" and row["attempts"] == 1 and row["last_error"] == "broker down"
    )
    assert row["next_attempt_at"] == NOW + timedelta(seconds=60)
    assert repo.settle_next(NOW + timedelta(seconds=59), lambda e: Published()) is None
    assert repo.settle_next(NOW + timedelta(seconds=60), lambda e: Published())
    assert rows(pool)[0]["status"] == "published" and rows(pool)[0]["last_error"] is None


def test_the_backoff_grows_with_each_failure_up_to_the_cap(
    pool: Pool, seed_garage: Callable[..., int]
) -> None:
    reserve_n(pool, seed_garage(1), 1)
    repo = OutboxRepo(pool)
    clock = NOW
    delays = []
    for _ in range(8):
        repo.settle_next(clock, lambda e, at=clock: RetryLater("x", retry_at(at, e)))
        due = rows(pool)[0]["next_attempt_at"]
        delays.append(int((due - clock).total_seconds()))  # type: ignore[operator]
        clock = due  # type: ignore[assignment]
    assert delays == [60, 120, 240, 480, 900, 900, 900, 900]


def test_a_parked_row_is_not_claimed_again(pool: Pool, seed_garage: Callable[..., int]) -> None:
    reserve_n(pool, seed_garage(1), 1)
    repo = OutboxRepo(pool)
    repo.settle_next(NOW, lambda e: Parked("oversize"))
    assert rows(pool)[0]["status"] == "parked" and rows(pool)[0]["attempts"] == 1
    assert repo.settle_next(NOW + 10 * HOUR, lambda e: Published()) is None


def test_rows_are_claimed_oldest_first(pool: Pool, seed_garage: Callable[..., int]) -> None:
    reserve_n(pool, seed_garage(3), 3)
    seen: list[int] = []
    repo = OutboxRepo(pool)
    while repo.settle_next(NOW, lambda e: (seen.append(e.outbox_id), Published())[1]):
        pass
    assert seen == sorted(seen) and len(seen) == 3


def test_a_failure_inside_settle_rolls_the_claim_back(
    pool: Pool, seed_garage: Callable[..., int]
) -> None:
    reserve_n(pool, seed_garage(1), 1)

    def explode(event: OutboxEvent) -> Published:
        raise RuntimeError("defect")

    with pytest.raises(RuntimeError):
        OutboxRepo(pool).settle_next(NOW, explode)
    row = rows(pool)[0]
    assert row["status"] == "pending" and row["attempts"] == 0


def test_concurrent_sweeps_never_hold_the_same_row(
    pool: Pool, seed_garage: Callable[..., int]
) -> None:
    reserve_n(pool, seed_garage(4), 4)
    repo = OutboxRepo(pool)
    claimed: list[int] = []
    lock = threading.Lock()
    barrier = threading.Barrier(4)

    def settle(event: OutboxEvent) -> Published:
        with lock:
            claimed.append(event.outbox_id)
        barrier.wait(timeout=10)  # every thread holds its row before any commits
        return Published()

    results: list[object] = []

    def sweep() -> None:
        results.append(repo.settle_next(NOW, settle))

    threads = [threading.Thread(target=sweep) for _ in range(4)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    assert sorted(claimed) == sorted(set(claimed)) and len(claimed) == 4
    assert all(r["status"] == "published" for r in rows(pool))


def test_an_operator_can_redrive_a_published_or_parked_row(
    pool: Pool, seed_garage: Callable[..., int]
) -> None:
    reserve_n(pool, seed_garage(2), 2)
    repo = OutboxRepo(pool)
    repo.settle_next(NOW, lambda e: Published())
    repo.settle_next(NOW, lambda e: Parked("fixed later"))
    with pool.connection() as conn:
        conn.execute(
            "UPDATE outbox SET status = 'pending', published_at = NULL, attempts = 0,"
            " next_attempt_at = %s, updated_at = %s WHERE status IN ('published', 'parked')",
            (NOW, NOW),
        )
    again: list[int] = []
    while repo.settle_next(NOW, lambda e: (again.append(e.outbox_id), Published())[1]):
        pass
    assert len(again) == 2


def test_the_database_refuses_a_published_row_without_its_stamp(
    pool: Pool, seed_garage: Callable[..., int]
) -> None:
    reserve_n(pool, seed_garage(1), 1)
    with pytest.raises(psycopg.errors.CheckViolation), pool.connection() as conn:
        conn.execute("UPDATE outbox SET status = 'published'")


def test_stuck_rows_are_the_pending_ones_with_enough_failed_attempts(
    pool: Pool, seed_garage: Callable[..., int]
) -> None:
    reserve_n(pool, seed_garage(3), 3)
    repo = OutboxRepo(pool)
    with pool.connection() as conn:
        conn.execute(
            "UPDATE outbox SET attempts = 10 WHERE outbox_id = (SELECT min(outbox_id) FROM outbox)"
        )
        conn.execute(
            "UPDATE outbox SET attempts = 12, status = 'parked'"
            " WHERE outbox_id = (SELECT max(outbox_id) FROM outbox)"
        )
        first = conn.execute("SELECT event_id FROM outbox ORDER BY outbox_id LIMIT 1").fetchone()
    assert repo.stuck_event_ids(10) == [first["event_id"]]  # type: ignore[index]
    assert repo.stuck_event_ids(13) == []
