"""Who may call the transition and lookup routes (R13, R17)."""

from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from parking_reservation.api.app import create_app
from tests.stubbed.fakes import FakeGarageStore, FakeReservationStore, booked
from tests.stubbed.wiring import build_services
from tests.support import NOW, SETTINGS, FakeVerifier


def headers(role: str, actor: str = "a") -> dict[str, str]:
    return {"Authorization": "Bearer fe-token", "X-Actor-Id": actor, "X-Actor-Role": role}


@pytest.fixture
def client() -> TestClient:
    store = FakeReservationStore()
    store.transition_result = booked(uuid4(), 1, NOW, NOW, "a")
    store.day_result = [booked(uuid4(), 1, NOW, NOW, "a")]
    app = create_app(SETTINGS, build_services(store, FakeGarageStore({1})), FakeVerifier())
    return TestClient(app, raise_server_exceptions=False)


@pytest.mark.parametrize("action", ["check-in", "check-out", "cancel"])
def test_a_driver_may_act_and_staff_may_not(client: TestClient, action: str) -> None:
    path = f"/v1/reservations/{uuid4()}/{action}"
    assert client.post(path, headers=headers("driver")).status_code == 200
    forbidden = client.post(path, headers=headers("staff"))
    assert forbidden.status_code == 403 and forbidden.json()["code"] == "FORBIDDEN"


def test_a_malformed_reservation_id_is_an_invalid_request(client: TestClient) -> None:
    response = client.post("/v1/reservations/not-a-uuid/cancel", headers=headers("driver"))
    assert response.status_code == 400 and response.json()["code"] == "INVALID_REQUEST"


def test_staff_may_list_and_drivers_may_not(client: TestClient) -> None:
    path = "/v1/garages/1/reservations?date=2026-03-01"
    ok = client.get(path, headers=headers("staff"))
    assert ok.status_code == 200 and len(ok.json()["reservations"]) == 1
    assert client.get(path, headers=headers("driver")).status_code == 403


@pytest.mark.parametrize(
    "query",
    [
        "",
        "?date=garbage",
        "?date=2026-13-40",
        "?date=1654646400",
        "?date=2026-11-23T00:00:00Z",
    ],
)
def test_the_lookup_needs_a_valid_date(client: TestClient, query: str) -> None:
    response = client.get(f"/v1/garages/1/reservations{query}", headers=headers("staff"))
    assert response.status_code == 400 and response.json()["code"] == "INVALID_REQUEST"


@pytest.mark.parametrize("garage", ["0", str(2**31), "x"])
def test_the_lookup_bounds_the_garage_id(client: TestClient, garage: str) -> None:
    response = client.get(
        f"/v1/garages/{garage}/reservations?date=2026-03-01", headers=headers("staff")
    )
    assert response.status_code == 400 and response.json()["code"] == "INVALID_REQUEST"
