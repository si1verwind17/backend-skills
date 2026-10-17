"""End-to-end API integration test: real Postgres (via the shared
`postgres_dsn`/`pool` fixtures), the real FastAPI app and its lifespan
wiring, only the Pub/Sub client swapped for the in-memory fake (no
GCP_PROJECT_ID set -> app/main.py's own fallback). Exercises the full
UC1-UC6 lifecycle through HTTP, including the boundary error handlers.
"""

from __future__ import annotations

import pytest
import pytest_asyncio
from fastapi.testclient import TestClient

from app.main import create_app
from tests.integration.helpers import seed_garage, seed_spot

pytestmark = pytest.mark.integration


@pytest.fixture
def client(postgres_dsn: str, monkeypatch: pytest.MonkeyPatch) -> TestClient:
    monkeypatch.setenv("DATABASE_URL", postgres_dsn)
    monkeypatch.setenv("INTERNAL_ENDPOINT_TOKEN", "test-secret")
    monkeypatch.delenv("GCP_PROJECT_ID", raising=False)
    app = create_app()
    with TestClient(app) as c:
        yield c


@pytest_asyncio.fixture
async def garage_and_spot(pool) -> int:
    garage_id = await seed_garage(pool, timezone="UTC")
    await seed_spot(pool, garage_id, "A1")
    return garage_id


def test_healthz(client: TestClient) -> None:
    resp = client.get("/healthz")
    assert resp.status_code == 200


def test_full_reservation_lifecycle_over_http(client: TestClient, garage_and_spot: int) -> None:
    garage_id = garage_and_spot

    create_resp = client.post(
        "/v1/reservations",
        json={
            "garage_id": garage_id,
            "driver_id": 42,
            "window_start": "2026-08-15T12:00:00Z",
            "window_end": "2026-08-15T14:00:00Z",
        },
    )
    assert create_resp.status_code == 201
    reservation = create_resp.json()
    assert reservation["status"] == "reserved"
    public_id = reservation["public_id"]

    check_in_resp = client.post(f"/v1/reservations/{public_id}/check-in")
    assert check_in_resp.status_code == 200
    assert check_in_resp.json()["status"] == "checked_in"

    complete_resp = client.post(f"/v1/reservations/{public_id}/complete")
    assert complete_resp.status_code == 200
    assert complete_resp.json()["status"] == "completed"

    # UC5: mobile app lists the driver's reservations.
    list_resp = client.get("/v1/drivers/42/reservations")
    assert list_resp.status_code == 200
    assert [r["public_id"] for r in list_resp.json()] == [public_id]


def test_cancel_after_check_in_returns_409(client: TestClient, garage_and_spot: int) -> None:
    garage_id = garage_and_spot
    create_resp = client.post(
        "/v1/reservations",
        json={
            "garage_id": garage_id,
            "driver_id": 1,
            "window_start": "2026-08-15T12:00:00Z",
            "window_end": "2026-08-15T14:00:00Z",
        },
    )
    public_id = create_resp.json()["public_id"]
    client.post(f"/v1/reservations/{public_id}/check-in")

    resp = client.post(f"/v1/reservations/{public_id}/cancel")

    assert resp.status_code == 409
    assert resp.json()["error"] == "conflict"


def test_invalid_window_returns_422(client: TestClient, garage_and_spot: int) -> None:
    garage_id = garage_and_spot
    resp = client.post(
        "/v1/reservations",
        json={
            "garage_id": garage_id,
            "driver_id": 1,
            "window_start": "2026-08-15T14:00:00Z",
            "window_end": "2026-08-15T12:00:00Z",
        },
    )

    assert resp.status_code == 422


def test_garage_full_returns_409(client: TestClient, garage_and_spot: int) -> None:
    garage_id = garage_and_spot
    client.post(
        "/v1/reservations",
        json={
            "garage_id": garage_id,
            "driver_id": 1,
            "window_start": "2026-08-15T12:00:00Z",
            "window_end": "2026-08-15T14:00:00Z",
        },
    )

    resp = client.post(
        "/v1/reservations",
        json={
            "garage_id": garage_id,
            "driver_id": 2,
            "window_start": "2026-08-15T13:00:00Z",
            "window_end": "2026-08-15T15:00:00Z",
        },
    )

    assert resp.status_code == 409


def test_garage_lookup_by_date_over_http(client: TestClient, garage_and_spot: int) -> None:
    garage_id = garage_and_spot
    client.post(
        "/v1/reservations",
        json={
            "garage_id": garage_id,
            "driver_id": 1,
            "window_start": "2026-08-15T12:00:00Z",
            "window_end": "2026-08-15T14:00:00Z",
        },
    )

    resp = client.get(f"/v1/garages/{garage_id}/reservations", params={"date": "2026-08-15"})

    assert resp.status_code == 200
    assert len(resp.json()) == 1


def test_internal_outbox_publish_requires_token(client: TestClient) -> None:
    resp = client.post("/internal/outbox/publish")
    assert resp.status_code == 403


def test_internal_outbox_publish_flow(client: TestClient, garage_and_spot: int) -> None:
    garage_id = garage_and_spot
    create_resp = client.post(
        "/v1/reservations",
        json={
            "garage_id": garage_id,
            "driver_id": 1,
            "window_start": "2026-08-15T12:00:00Z",
            "window_end": "2026-08-15T14:00:00Z",
        },
    )
    public_id = create_resp.json()["public_id"]
    client.post(f"/v1/reservations/{public_id}/check-in")
    client.post(f"/v1/reservations/{public_id}/complete")

    resp = client.post("/internal/outbox/publish", headers={"X-Internal-Token": "test-secret"})

    assert resp.status_code == 200
    body = resp.json()
    assert body == {"claimed": 1, "published": 1, "failed": 0}
