from collections.abc import Iterator
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import UUID

import psycopg
import pytest

from parking_reservation.core.event_topics import CANCELLED_TOPIC, CHECKED_IN_TOPIC, COMPLETED_TOPIC
from parking_reservation.core.new_reservation import NewReservation
from parking_reservation.core.reservation import Reservation
from parking_reservation.core.reservation_status import ReservationStatus as S
from parking_reservation.core.transition_action import TransitionAction as A
from parking_reservation.repo.postgres_garage_repo import PostgresGarageRepo
from parking_reservation.repo.postgres_reservation_repo import PostgresReservationRepo
from parking_reservation.sys.database import DictPool, open_pool
from testkit.sequential_id_source import SequentialIdSource

pytestmark = pytest.mark.integration

NOW = datetime(2026, 10, 20, 9, 0, tzinfo=UTC)
T10 = datetime(2026, 10, 20, 10, 0, tzinfo=UTC)
T12 = datetime(2026, 10, 20, 12, 0, tzinfo=UTC)
CHECK_IN = datetime(2026, 10, 20, 10, 5, tzinfo=UTC)
CHECK_OUT = datetime(2026, 10, 20, 11, 30, tzinfo=UTC)


@pytest.fixture
def pool(seeded: str) -> Iterator[DictPool]:
    p = open_pool(seeded)
    yield p
    p.close()


@pytest.fixture
def repo(pool: DictPool) -> PostgresReservationRepo:
    return PostgresReservationRepo(pool)


class _Ids:
    """Event ids for transitions start at 1000 so they never collide with create's ids."""

    def __init__(self) -> None:
        self._source = SequentialIdSource()
        self._next = 1000

    def event(self) -> UUID:
        self._next += 1
        return UUID(int=self._next)

    def create(self) -> tuple[UUID, UUID]:
        return self._source.new_id(), self._source.new_id()


@pytest.fixture
def ids() -> _Ids:
    return _Ids()


def _book(repo: PostgresReservationRepo, ids: _Ids, driver: str = "d1", garage: str = "G1") -> Reservation:
    public_id, event_id = ids.create()
    result = repo.create(NewReservation(public_id, event_id, garage, driver, f"k-{driver}", T10, T12), NOW)
    assert result.reservation is not None
    return result.reservation


def _events(seeded: str) -> list[tuple[str, str, dict[str, Any]]]:
    with psycopg.connect(seeded) as conn:
        return [
            (r[0], r[1], r[2])
            for r in conn.execute(
                "SELECT topic, status, payload FROM outbox_event ORDER BY created_at, event_id"
            )
        ]


def test_full_lifecycle_records_one_event_per_transition_with_the_new_state(repo, ids, seeded) -> None:
    r = _book(repo, ids)
    assert repo.apply_transition(r.public_id, "d1", A.CHECK_IN, ids.event(), CHECK_IN)
    assert repo.apply_transition(r.public_id, "d1", A.CHECK_OUT, ids.event(), CHECK_OUT)
    done = repo.find_for_driver(r.public_id, "d1")
    assert done is not None
    assert (done.status, done.checked_in_at, done.checked_out_at) == (S.COMPLETED, CHECK_IN, CHECK_OUT)
    events = {topic: payload for topic, _, payload in _events(seeded)}
    assert set(events) >= {CHECKED_IN_TOPIC, COMPLETED_TOPIC}
    completed = events[COMPLETED_TOPIC]
    assert completed["status"] == "completed"
    assert completed["checked_in_at"] == "2026-10-20T10:05:00+00:00"
    assert completed["checked_out_at"] == "2026-10-20T11:30:00+00:00"
    assert completed["occurred_at"] == "2026-10-20T11:30:00+00:00"
    assert (completed["garage_code"], completed["spot_label"], completed["driver_id"]) == ("G1", "A1", "d1")
    assert completed["reservation_public_id"] == str(r.public_id)
    assert events[CHECKED_IN_TOPIC]["status"] == "checked_in"


def test_a_repeat_applies_nothing_and_adds_no_event(repo, ids, seeded) -> None:
    r = _book(repo, ids)
    assert repo.apply_transition(r.public_id, "d1", A.CHECK_IN, ids.event(), CHECK_IN)
    assert not repo.apply_transition(r.public_id, "d1", A.CHECK_IN, ids.event(), CHECK_IN)
    assert len(_events(seeded)) == 2  # reserved + checked-in


def test_another_drivers_reservation_is_untouched(repo, ids) -> None:
    r = _book(repo, ids)
    assert not repo.apply_transition(r.public_id, "intruder", A.CANCEL, ids.event(), CHECK_IN)
    assert repo.find_for_driver(r.public_id, "intruder") is None
    assert repo.find_for_driver(r.public_id, "d1") == r


def test_check_in_is_refused_by_the_database_at_or_after_the_end(repo, ids) -> None:
    r = _book(repo, ids)
    assert not repo.apply_transition(r.public_id, "d1", A.CHECK_IN, ids.event(), T12)


def test_cancel_frees_the_window_and_records_the_event(repo, ids, seeded) -> None:
    r = _book(repo, ids, garage="G2")
    assert repo.apply_transition(r.public_id, "d1", A.CANCEL, ids.event(), CHECK_IN)
    again = _book(repo, ids, driver="d2", garage="G2")
    assert again.spot_label == "B1"
    assert CANCELLED_TOPIC in [t for t, _, _ in _events(seeded)]


def test_cancel_and_check_in_race_has_exactly_one_winner(repo, ids) -> None:
    r = _book(repo, ids)
    actions = [A.CHECK_IN, A.CANCEL] * 4
    with ThreadPoolExecutor(max_workers=8) as executor:
        wins = list(
            executor.map(
                lambda a: repo.apply_transition(r.public_id, "d1", a, ids.event(), CHECK_IN), actions
            )
        )
    assert sum(wins) == 1
    final = repo.find_for_driver(r.public_id, "d1")
    assert final is not None and final.status in (S.CHECKED_IN, S.CANCELLED)


def test_list_overlapping_orders_by_start_then_spot_and_includes_every_status(repo, ids) -> None:
    first = _book(repo, ids, driver="d1")  # spot A1, 10:00-12:00
    public_id, event_id = ids.create()
    earlier = repo.create(
        NewReservation(
            public_id, event_id, "G1", "d2", "k2", T10 - timedelta(hours=1), T10 + timedelta(hours=1)
        ),
        NOW,
    ).reservation
    assert earlier is not None and earlier.spot_label == "A2"  # earlier start, later spot label
    public_id, event_id = ids.create()
    later = repo.create(
        NewReservation(public_id, event_id, "G1", "d3", "k3", T12, T12 + timedelta(hours=1)), NOW
    ).reservation
    assert later is not None
    repo.apply_transition(later.public_id, "d3", A.CANCEL, ids.event(), CHECK_IN)
    listed = repo.list_overlapping("G1", T10 - timedelta(hours=1), T12 + timedelta(hours=1))
    assert [r.public_id for r in listed] == [earlier.public_id, first.public_id, later.public_id]
    assert listed[2].status is S.CANCELLED
    assert [r.public_id for r in repo.list_overlapping("G1", T12, T12 + timedelta(hours=1))] == [
        later.public_id
    ]
    assert repo.list_overlapping("G2", T10, T12) == []


def test_garage_time_zone_lookup(pool) -> None:
    garages = PostgresGarageRepo(pool)
    assert garages.find_time_zone("G2") == "Europe/Zurich"
    assert garages.find_time_zone("NOPE") is None


def test_the_day_boundary_uses_the_half_open_window(repo, ids) -> None:
    public_id, event_id = ids.create()
    repo.create(NewReservation(public_id, event_id, "G1", "d1", "k", T10, T12), NOW)
    assert repo.list_overlapping("G1", T12, T12 + timedelta(days=1)) == []
    assert len(repo.list_overlapping("G1", T12 - timedelta(seconds=1), T12 + timedelta(days=1))) == 1
