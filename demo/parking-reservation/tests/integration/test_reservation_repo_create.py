from collections.abc import Iterator
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime, timedelta
from uuid import UUID

import psycopg
import pytest

from parking_reservation.core.create_outcome import CreateOutcome
from parking_reservation.core.event_topics import RESERVED_TOPIC
from parking_reservation.core.new_reservation import NewReservation
from parking_reservation.repo.postgres_reservation_repo import PostgresReservationRepo
from parking_reservation.sys.database import DictPool, open_pool
from testkit.sequential_id_source import SequentialIdSource

pytestmark = pytest.mark.integration

NOW = datetime(2026, 10, 20, 9, 0, tzinfo=UTC)
T10 = datetime(2026, 10, 20, 10, 0, tzinfo=UTC)
T11 = T10 + timedelta(hours=1)
T12 = T10 + timedelta(hours=2)


@pytest.fixture
def pool(seeded: str) -> Iterator[DictPool]:
    p = open_pool(seeded)
    yield p
    p.close()


@pytest.fixture
def repo(pool: DictPool) -> PostgresReservationRepo:
    return PostgresReservationRepo(pool)


class _Maker:
    def __init__(self) -> None:
        self._ids = SequentialIdSource()

    def __call__(
        self, driver: str, key: str, start: datetime, end: datetime, garage: str = "G1"
    ) -> NewReservation:
        return NewReservation(self._ids.new_id(), self._ids.new_id(), garage, driver, key, start, end)


@pytest.fixture
def make() -> _Maker:
    return _Maker()


def test_create_assigns_the_first_spot_in_label_order_and_returns_the_reservation(repo, make) -> None:
    result = repo.create(make("d1", "k1", T10, T12), NOW)
    assert result.outcome is CreateOutcome.CREATED
    r = result.reservation
    assert r is not None
    assert (r.garage_code, r.spot_label, r.driver_id, r.start_at, r.end_at) == ("G1", "A1", "d1", T10, T12)
    assert r.status.value == "reserved"


def test_same_key_and_request_is_replayed_without_a_second_row(repo, make, seeded) -> None:
    first = repo.create(make("d1", "k1", T10, T12), NOW)
    again = repo.create(make("d1", "k1", T10, T12), NOW)
    assert again.outcome is CreateOutcome.REPLAYED
    assert again.reservation == first.reservation
    with psycopg.connect(seeded) as conn:
        assert conn.execute("SELECT count(*) FROM reservation").fetchone() == (1,)
        assert conn.execute("SELECT count(*) FROM outbox_event").fetchone() == (1,)


def test_same_key_with_another_window_is_key_reused(repo, make) -> None:
    repo.create(make("d1", "k1", T10, T12), NOW)
    assert repo.create(make("d1", "k1", T10, T11), NOW).outcome is CreateOutcome.KEY_REUSED


def test_the_same_key_for_another_driver_is_independent(repo, make) -> None:
    repo.create(make("d1", "k1", T10, T12), NOW)
    assert repo.create(make("d2", "k1", T10, T12), NOW).outcome is CreateOutcome.CREATED


def test_second_overlapping_request_gets_the_second_spot_then_no_spot(repo, make) -> None:
    repo.create(make("d1", "k1", T10, T12), NOW)
    second = repo.create(make("d2", "k2", T11, T12 + timedelta(hours=1)), NOW)
    assert second.reservation is not None and second.reservation.spot_label == "A2"
    assert repo.create(make("d3", "k3", T11, T12), NOW).outcome is CreateOutcome.NO_SPOT


def test_back_to_back_windows_share_a_spot(repo, make) -> None:
    repo.create(make("d1", "k1", T10, T11, garage="G2"), NOW)
    second = repo.create(make("d2", "k2", T11, T12, garage="G2"), NOW)
    assert second.outcome is CreateOutcome.CREATED
    assert second.reservation is not None and second.reservation.spot_label == "B1"


def test_unknown_garage(repo, make) -> None:
    assert (
        repo.create(make("d1", "k1", T10, T12, garage="NOPE"), NOW).outcome is CreateOutcome.GARAGE_NOT_FOUND
    )


def test_a_cancelled_reservation_frees_its_window(repo, make, seeded) -> None:
    repo.create(make("d1", "k1", T10, T12, garage="G2"), NOW)
    with psycopg.connect(seeded, autocommit=True) as conn:
        conn.execute(
            "UPDATE reservation SET status = 'cancelled', cancelled_at = %s, updated_at = %s", (NOW, NOW)
        )
    assert repo.create(make("d2", "k2", T10, T12, garage="G2"), NOW).outcome is CreateOutcome.CREATED


def test_find_by_key(repo, make) -> None:
    assert repo.find_by_key("d1", "k1") is None
    created = repo.create(make("d1", "k1", T10, T12), NOW)
    assert repo.find_by_key("d1", "k1") == created.reservation


def test_last_spot_under_concurrency_goes_to_exactly_one_caller(repo, make, seeded) -> None:
    requests = [make(f"d{i}", "k", T10, T12, garage="G2") for i in range(8)]
    with ThreadPoolExecutor(max_workers=5) as executor:
        results = list(executor.map(lambda n: repo.create(n, NOW), requests))
    outcomes = sorted(r.outcome.value for r in results)
    assert outcomes == ["created"] + ["no_spot"] * 7
    with psycopg.connect(seeded) as conn:
        assert conn.execute("SELECT count(*) FROM reservation").fetchone() == (1,)


def test_the_reserved_event_is_recorded_with_the_new_state(repo, make, seeded) -> None:
    created = repo.create(make("d1", "k1", T10, T12), NOW)
    with psycopg.connect(seeded) as conn:
        row = conn.execute("SELECT event_id, topic, status, payload FROM outbox_event").fetchone()
    assert row is not None
    event_id, topic, status, payload = row
    assert (topic, status) == (RESERVED_TOPIC, "pending")
    assert event_id == UUID(int=2)
    assert created.reservation is not None
    assert payload["reservation_public_id"] == str(created.reservation.public_id)
    assert (payload["status"], payload["garage_code"], payload["spot_label"], payload["driver_id"]) == (
        "reserved",
        "G1",
        "A1",
        "d1",
    )
    assert payload["start_at"].endswith("+00:00") or payload["start_at"].endswith("Z")
