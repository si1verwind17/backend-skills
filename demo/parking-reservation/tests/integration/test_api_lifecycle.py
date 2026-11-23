"""UC2-UC5 through HTTP, the real repositories and a real Postgres."""

from collections.abc import Callable, Iterator
from datetime import timedelta

import pytest
from fastapi.testclient import TestClient

from parking_reservation.api.app import create_app
from parking_reservation.repo.database import Pool
from parking_reservation.repo.garage_repo import GarageRepo
from parking_reservation.repo.reservation_repo import ReservationRepo
from tests.stubbed.wiring import build_services
from tests.support import NOW, SETTINGS, FakeClock, FakeVerifier

HOUR = timedelta(hours=1)


@pytest.fixture
def clock() -> FakeClock:
    return FakeClock()


@pytest.fixture
def client(pool: Pool, clock: FakeClock) -> Iterator[TestClient]:
    repo = ReservationRepo(pool)
    app = create_app(SETTINGS, build_services(repo, GarageRepo(pool), clock), FakeVerifier())
    yield TestClient(app, raise_server_exceptions=False)


def as_(role: str, actor: str, key: str | None = None) -> dict[str, str]:
    base = {"Authorization": "Bearer fe-token", "X-Actor-Id": actor, "X-Actor-Role": role}
    return base | ({"Idempotency-Key": key} if key else {})


def reserve(client: TestClient, garage: int, driver: str = "d1", start=HOUR, end=2 * HOUR) -> str:  # type: ignore[no-untyped-def]
    body = {
        "garage_id": garage,
        "window_start": (NOW + start).isoformat(),
        "window_end": (NOW + end).isoformat(),
    }
    response = client.post("/v1/reservations", json=body, headers=as_("driver", driver, "k"))
    assert response.status_code == 201, response.text
    return str(response.json()["reservation_id"])


def act(client: TestClient, rid: str, action: str, driver: str = "d1"):  # type: ignore[no-untyped-def]
    return client.post(f"/v1/reservations/{rid}/{action}", headers=as_("driver", driver))


def test_reserve_check_in_check_out(
    client: TestClient, clock: FakeClock, seed_garage: Callable[..., int]
) -> None:
    rid = reserve(client, seed_garage(1))
    clock.advance(HOUR + timedelta(minutes=5))
    checked_in = act(client, rid, "check-in")
    assert checked_in.status_code == 200 and checked_in.json()["status"] == "CHECKED_IN"
    again = act(client, rid, "check-in")
    assert again.status_code == 200 and again.json() == checked_in.json()
    clock.advance(timedelta(minutes=20))
    done = act(client, rid, "check-out")
    assert done.status_code == 200 and done.json()["status"] == "COMPLETED"
    assert done.json()["checked_out_at"] is not None
    assert act(client, rid, "check-out").json() == done.json()


def test_check_in_is_refused_outside_the_window(
    client: TestClient, seed_garage: Callable[..., int]
) -> None:
    rid = reserve(client, seed_garage(1))
    early = act(client, rid, "check-in")
    assert early.status_code == 409 and early.json()["code"] == "OUTSIDE_WINDOW"


def test_check_out_needs_a_check_in_first(
    client: TestClient, seed_garage: Callable[..., int]
) -> None:
    rid = reserve(client, seed_garage(1))
    refused = act(client, rid, "check-out")
    assert refused.status_code == 409 and refused.json()["code"] == "ILLEGAL_TRANSITION"


def test_cancel_before_check_in_frees_the_spot(
    client: TestClient, seed_garage: Callable[..., int]
) -> None:
    garage = seed_garage(1)
    rid = reserve(client, garage)
    cancelled = act(client, rid, "cancel")
    assert cancelled.status_code == 200 and cancelled.json()["status"] == "CANCELLED"
    assert act(client, rid, "cancel").json() == cancelled.json()
    body = {
        "garage_id": garage,
        "window_start": (NOW + HOUR).isoformat(),
        "window_end": (NOW + 2 * HOUR).isoformat(),
    }
    other = client.post("/v1/reservations", json=body, headers=as_("driver", "d2", "k2"))
    assert other.status_code == 201


def test_cancel_after_check_in_is_refused(
    client: TestClient, clock: FakeClock, seed_garage: Callable[..., int]
) -> None:
    rid = reserve(client, seed_garage(1))
    clock.advance(HOUR)
    act(client, rid, "check-in")
    refused = act(client, rid, "cancel")
    assert refused.status_code == 409 and refused.json()["code"] == "ILLEGAL_TRANSITION"


def test_a_cancelled_reservation_cannot_be_checked_in(
    client: TestClient, clock: FakeClock, seed_garage: Callable[..., int]
) -> None:
    rid = reserve(client, seed_garage(1))
    act(client, rid, "cancel")
    clock.advance(HOUR)
    refused = act(client, rid, "check-in")
    assert refused.status_code == 409 and refused.json()["code"] == "ILLEGAL_TRANSITION"


def test_another_driver_gets_not_found_and_changes_nothing(
    client: TestClient, seed_garage: Callable[..., int]
) -> None:
    rid = reserve(client, seed_garage(1))
    for action in ("check-in", "check-out", "cancel"):
        refused = act(client, rid, action, driver="intruder")
        assert refused.status_code == 404 and refused.json()["code"] == "NOT_FOUND"
    mine = client.get(f"/v1/reservations/{rid}", headers=as_("driver", "d1"))
    assert mine.json()["status"] == "BOOKED"


def test_staff_see_the_garages_day(client: TestClient, seed_garage: Callable[..., int]) -> None:
    garage = seed_garage(2)
    first = reserve(client, garage, "d1")
    act(client, first, "cancel")
    reserve(client, garage, "d2")
    listed = client.get(
        f"/v1/garages/{garage}/reservations?date=2026-03-01", headers=as_("staff", "s1")
    )
    assert listed.status_code == 200
    data = listed.json()
    assert data["garage_id"] == garage and data["date"] == "2026-03-01"
    assert sorted(r["status"] for r in data["reservations"]) == ["BOOKED", "CANCELLED"]
    assert sorted(r["driver_id"] for r in data["reservations"]) == ["d1", "d2"]


def test_the_lookup_reports_an_unknown_garage(client: TestClient) -> None:
    missing = client.get("/v1/garages/9/reservations?date=2026-03-01", headers=as_("staff", "s1"))
    assert missing.status_code == 404 and missing.json()["code"] == "GARAGE_NOT_FOUND"


def test_the_day_before_is_empty(client: TestClient, seed_garage: Callable[..., int]) -> None:
    garage = seed_garage(1)
    reserve(client, garage)
    other_day = client.get(
        f"/v1/garages/{garage}/reservations?date=2026-02-28", headers=as_("staff", "s1")
    )
    assert other_day.status_code == 200 and other_day.json()["reservations"] == []
