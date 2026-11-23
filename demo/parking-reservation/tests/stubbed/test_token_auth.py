"""The token middleware and identity headers, with a fake verifier and stub services."""

from datetime import timedelta
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from parking_reservation.api.app import create_app
from tests.stubbed.fakes import FakeGarageStore, FakeReservationStore, booked
from tests.stubbed.wiring import build_services
from tests.support import NOW, SETTINGS, FakeVerifier


@pytest.fixture
def verifier() -> FakeVerifier:
    return FakeVerifier()


@pytest.fixture
def client(verifier: FakeVerifier) -> TestClient:
    store = FakeReservationStore()
    mine = booked(uuid4(), 1, NOW + timedelta(hours=1), NOW + timedelta(hours=2), "drv")
    store.by_key[("drv", "k")] = mine
    store.book_result = mine
    services = build_services(store, FakeGarageStore({1}))
    app = create_app(SETTINGS, services, verifier)
    test_client = TestClient(app, raise_server_exceptions=False)
    test_client.mine = mine  # type: ignore[attr-defined]
    return test_client


def actor(token: str, actor_id: str = "drv", role: str = "driver") -> dict[str, str]:
    return {"Authorization": f"Bearer {token}", "X-Actor-Id": actor_id, "X-Actor-Role": role}


def test_health_needs_no_token(client: TestClient) -> None:
    assert client.get("/health").status_code == 200


def test_a_call_without_a_token_is_unauthenticated(client: TestClient) -> None:
    response = client.get(f"/v1/reservations/{client.mine.public_id}")  # type: ignore[attr-defined]
    assert response.status_code == 401 and response.json()["code"] == "UNAUTHENTICATED"


@pytest.mark.parametrize("header", ["Basic abc", "Bearer", "Bearer   ", "bearer bad-token"])
def test_a_bad_authorization_header_is_unauthenticated(client: TestClient, header: str) -> None:
    response = client.get("/v1/reservations/" + str(uuid4()), headers={"Authorization": header})
    assert response.status_code == 401


def test_the_scheduler_cannot_use_v1(client: TestClient) -> None:
    response = client.get(f"/v1/reservations/{client.mine.public_id}", headers=actor("sc-token"))  # type: ignore[attr-defined]
    assert response.status_code == 403 and response.json()["code"] == "FORBIDDEN"


def test_an_unknown_account_is_forbidden(client: TestClient) -> None:
    response = client.get(f"/v1/reservations/{client.mine.public_id}", headers=actor("other-token"))  # type: ignore[attr-defined]
    assert response.status_code == 403


def test_other_paths_are_forbidden_even_for_known_accounts(client: TestClient) -> None:
    assert client.get("/docs", headers=actor("fe-token")).status_code == 403
    assert client.get("/openapi.json", headers=actor("fe-token")).status_code == 403


def test_key_fetch_failure_is_a_retryable_503(client: TestClient, verifier: FakeVerifier) -> None:
    verifier.unavailable = True
    response = client.get("/v1/reservations/" + str(uuid4()), headers=actor("fe-token"))
    assert response.status_code == 503 and response.json()["code"] == "UNAVAILABLE"


def test_the_front_end_with_driver_headers_reads_its_reservation(client: TestClient) -> None:
    response = client.get(f"/v1/reservations/{client.mine.public_id}", headers=actor("fe-token"))  # type: ignore[attr-defined]
    assert response.status_code == 200 and response.json()["status"] == "BOOKED"


@pytest.mark.parametrize(
    ("headers", "status", "code"),
    [
        ({"Authorization": "Bearer fe-token"}, 401, "UNAUTHENTICATED"),
        ({"Authorization": "Bearer fe-token", "X-Actor-Id": "drv"}, 401, "UNAUTHENTICATED"),
        (actor("fe-token", role="janitor"), 403, "FORBIDDEN"),
        (actor("fe-token", role="staff"), 403, "FORBIDDEN"),
        (actor("fe-token", actor_id="x" * 129), 401, "UNAUTHENTICATED"),
    ],
)
def test_actor_headers_are_checked(client: TestClient, headers, status, code) -> None:  # type: ignore[no-untyped-def]
    response = client.get(f"/v1/reservations/{client.mine.public_id}", headers=headers)  # type: ignore[attr-defined]
    assert response.status_code == status and response.json()["code"] == code


def test_another_drivers_reservation_is_not_found(client: TestClient) -> None:
    response = client.get(
        f"/v1/reservations/{client.mine.public_id}",  # type: ignore[attr-defined]
        headers=actor("fe-token", actor_id="intruder"),
    )
    assert response.status_code == 404 and response.json()["code"] == "NOT_FOUND"


def test_an_oversized_garage_id_is_an_invalid_request(client: TestClient) -> None:
    headers = actor("fe-token") | {"Idempotency-Key": "k1"}
    response = client.post("/v1/reservations", json=reserve_body(garage_id=2**40), headers=headers)
    assert response.status_code == 400 and response.json()["code"] == "INVALID_REQUEST"


def reserve_body(**override: object) -> dict[str, object]:
    body: dict[str, object] = {
        "garage_id": 1,
        "window_start": (NOW + timedelta(hours=1)).isoformat(),
        "window_end": (NOW + timedelta(hours=2)).isoformat(),
    }
    return body | override


@pytest.mark.parametrize(
    "override",
    [
        {"window_start": "2026-03-01T13:00:00"},
        {"garage_id": 0},
        {"garage_id": "x"},
        {"extra": 1},
        {"window_end": "garbage"},
    ],
)
def test_malformed_reserve_bodies_are_invalid_requests(client: TestClient, override) -> None:  # type: ignore[no-untyped-def]
    headers = actor("fe-token") | {"Idempotency-Key": "k1"}
    response = client.post("/v1/reservations", json=reserve_body(**override), headers=headers)
    assert response.status_code == 400 and response.json()["code"] == "INVALID_REQUEST"


@pytest.mark.parametrize("key", [None, "", "k" * 129])
def test_the_idempotency_key_is_required_and_bounded(client: TestClient, key: str | None) -> None:
    headers = actor("fe-token") | ({"Idempotency-Key": key} if key is not None else {})
    response = client.post("/v1/reservations", json=reserve_body(), headers=headers)
    assert response.status_code == 400 and response.json()["code"] == "INVALID_REQUEST"


def test_a_driver_reserves(client: TestClient) -> None:
    headers = actor("fe-token") | {"Idempotency-Key": "new-key"}
    response = client.post("/v1/reservations", json=reserve_body(), headers=headers)
    assert response.status_code == 201 and response.json()["status"] == "BOOKED"
