"""UC1 and UC7 through the HTTP layer, the real repositories and a real Postgres."""

from collections.abc import Callable, Iterator
from datetime import timedelta

import pytest
from fastapi.testclient import TestClient

from parking_reservation.api.app import create_app
from parking_reservation.repo.database import Pool
from parking_reservation.repo.garage_repo import GarageRepo
from parking_reservation.repo.reservation_repo import ReservationRepo
from tests.stubbed.wiring import build_services
from tests.support import NOW, SETTINGS, FakeVerifier


@pytest.fixture
def client(pool: Pool) -> Iterator[TestClient]:
    reservations = ReservationRepo(pool)
    services = build_services(reservations, GarageRepo(pool))
    yield TestClient(create_app(SETTINGS, services, FakeVerifier()), raise_server_exceptions=False)


def headers(driver: str = "d1", key: str | None = None) -> dict[str, str]:
    base = {"Authorization": "Bearer fe-token", "X-Actor-Id": driver, "X-Actor-Role": "driver"}
    return base | ({"Idempotency-Key": key} if key else {})


def body(garage: int, start_h: int = 1, end_h: int = 2) -> dict[str, object]:
    return {
        "garage_id": garage,
        "window_start": (NOW + timedelta(hours=start_h)).isoformat(),
        "window_end": (NOW + timedelta(hours=end_h)).isoformat(),
    }


def test_reserve_then_view(client: TestClient, seed_garage: Callable[..., int]) -> None:
    garage = seed_garage(1)
    created = client.post("/v1/reservations", json=body(garage), headers=headers(key="k1"))
    assert created.status_code == 201
    data = created.json()
    assert data["status"] == "BOOKED" and data["garage_id"] == garage and data["driver_id"] == "d1"
    read = client.get(f"/v1/reservations/{data['reservation_id']}", headers=headers())
    assert read.status_code == 200 and read.json() == data


def test_a_repeated_request_returns_the_same_reservation(
    client: TestClient, seed_garage: Callable[..., int]
) -> None:
    garage = seed_garage(2)
    first = client.post("/v1/reservations", json=body(garage), headers=headers(key="k1"))
    again = client.post("/v1/reservations", json=body(garage), headers=headers(key="k1"))
    assert again.status_code == 201 and again.json() == first.json()


def test_a_reused_key_with_another_window_conflicts(
    client: TestClient, seed_garage: Callable[..., int]
) -> None:
    garage = seed_garage(2)
    client.post("/v1/reservations", json=body(garage), headers=headers(key="k1"))
    other = client.post("/v1/reservations", json=body(garage, 3, 4), headers=headers(key="k1"))
    assert other.status_code == 409 and other.json()["code"] == "IDEMPOTENCY_KEY_REUSED"


def test_the_same_key_of_two_drivers_books_twice(
    client: TestClient, seed_garage: Callable[..., int]
) -> None:
    garage = seed_garage(2)
    one = client.post("/v1/reservations", json=body(garage), headers=headers("d1", "k"))
    two = client.post("/v1/reservations", json=body(garage), headers=headers("d2", "k"))
    assert one.json()["spot_id"] != two.json()["spot_id"]


def test_garage_full_and_unknown_garage(
    client: TestClient, seed_garage: Callable[..., int]
) -> None:
    garage = seed_garage(1)
    client.post("/v1/reservations", json=body(garage), headers=headers(key="k1"))
    full = client.post("/v1/reservations", json=body(garage), headers=headers("d2", "k2"))
    assert full.status_code == 409 and full.json()["code"] == "GARAGE_FULL"
    missing = client.post("/v1/reservations", json=body(garage + 9), headers=headers(key="k3"))
    assert missing.status_code == 404 and missing.json()["code"] == "GARAGE_NOT_FOUND"


def test_an_invalid_window_is_unprocessable_and_stores_nothing(
    client: TestClient, seed_garage: Callable[..., int], pool: Pool
) -> None:
    garage = seed_garage(1)
    response = client.post("/v1/reservations", json=body(garage, 2, 1), headers=headers(key="k1"))
    assert response.status_code == 422 and response.json()["code"] == "INVALID_WINDOW"
    with pool.connection() as conn:
        assert conn.execute("SELECT count(*) AS n FROM reservation").fetchone()["n"] == 0  # type: ignore[index]


def test_another_driver_cannot_view_it(client: TestClient, seed_garage: Callable[..., int]) -> None:
    garage = seed_garage(1)
    created = client.post("/v1/reservations", json=body(garage), headers=headers(key="k1")).json()
    peek = client.get(f"/v1/reservations/{created['reservation_id']}", headers=headers("d2"))
    assert peek.status_code == 404
