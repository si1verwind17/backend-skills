"""End-to-end HTTP tests for the operator console, pricing, driver
account and internal scheduler endpoints: real Postgres, the real app
and its lifespan wiring, in-memory publishers (no GCP_PROJECT_ID)."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.main import create_app

pytestmark = pytest.mark.integration

INTERNAL = {"X-Internal-Token": "test-secret"}

ALL_DAYS = ["mon", "tue", "wed", "thu", "fri", "sat", "sun"]


@pytest.fixture
def client(postgres_dsn: str, monkeypatch: pytest.MonkeyPatch) -> TestClient:
    monkeypatch.setenv("DATABASE_URL", postgres_dsn)
    monkeypatch.setenv("INTERNAL_ENDPOINT_TOKEN", "test-secret")
    monkeypatch.delenv("GCP_PROJECT_ID", raising=False)
    with TestClient(create_app()) as c:
        yield c


def _operator(client: TestClient, name: str = "City Parking") -> int:
    resp = client.post("/v1/admin/operators", json={"name": name, "contact_email": "ops@example.com"})
    assert resp.status_code == 201
    return resp.json()["operator_id"]


def _garage(client: TestClient, operator_id: int, *, timezone: str = "UTC", spots: int = 2) -> int:
    resp = client.post(
        "/v1/admin/garages",
        json={"operator_id": operator_id, "name": "Downtown", "address": "1 Main St", "timezone": timezone},
    )
    assert resp.status_code == 201
    garage_id = resp.json()["garage_id"]
    if spots:
        resp = client.post(
            f"/v1/admin/garages/{garage_id}/spots/range",
            json={"prefix": "A", "first": 1, "last": spots, "spot_type": "standard", "level": "L1"},
        )
        assert resp.status_code == 201
    return garage_id


def _flat_tariff(client: TestClient, garage_id: int, *, rate: int = 100) -> dict:
    resp = client.post(
        f"/v1/admin/garages/{garage_id}/tariffs",
        json={
            "name": "Standard",
            "currency": "eur",
            "valid_from": "2026-01-01",
            "bands": [{"weekdays": ALL_DAYS, "starts": "00:00", "ends": "24:00", "rate_cents_per_block": rate}],
        },
    )
    assert resp.status_code == 201, resp.text
    return resp.json()


def _reserve(client: TestClient, garage_id: int, start: str, end: str, driver_id: int = 42) -> str:
    resp = client.post(
        "/v1/reservations",
        json={"garage_id": garage_id, "driver_id": driver_id, "window_start": start, "window_end": end},
    )
    assert resp.status_code == 201, resp.text
    return resp.json()["public_id"]


# --- operators and garages -------------------------------------------------


def test_operator_crud(client: TestClient) -> None:
    operator_id = _operator(client)

    assert client.get(f"/v1/admin/operators/{operator_id}").json()["name"] == "City Parking"
    patched = client.patch(f"/v1/admin/operators/{operator_id}", json={"contact_email": "new@example.com"})
    assert patched.status_code == 200
    assert patched.json()["contact_email"] == "new@example.com"
    assert [o["operator_id"] for o in client.get("/v1/admin/operators").json()] == [operator_id]


def test_duplicate_operator_returns_409(client: TestClient) -> None:
    _operator(client)

    resp = client.post("/v1/admin/operators", json={"name": "City Parking", "contact_email": "x@example.com"})

    assert resp.status_code == 409


def test_unknown_operator_returns_404(client: TestClient) -> None:
    assert client.get("/v1/admin/operators/999").status_code == 404
    assert client.get("/v1/admin/operators/999/garages").status_code == 404


def test_garage_with_unknown_timezone_returns_422(client: TestClient) -> None:
    operator_id = _operator(client)

    resp = client.post(
        "/v1/admin/garages", json={"operator_id": operator_id, "name": "X", "timezone": "Mars/Olympus"}
    )

    assert resp.status_code == 422


def test_garage_update_and_listing(client: TestClient) -> None:
    operator_id = _operator(client)
    garage_id = _garage(client, operator_id, spots=0)

    resp = client.patch(f"/v1/admin/garages/{garage_id}", json={"is_active": False})

    assert resp.status_code == 200
    assert client.get(f"/v1/admin/operators/{operator_id}/garages").json() == []
    listed = client.get(f"/v1/admin/operators/{operator_id}/garages", params={"include_inactive": "true"}).json()
    assert [g["garage_id"] for g in listed] == [garage_id]


def test_opening_hours_round_trip(client: TestClient) -> None:
    garage_id = _garage(client, _operator(client), spots=0)

    put = client.put(
        f"/v1/admin/garages/{garage_id}/opening-hours",
        json={"days": [{"weekday": "sat", "opens": "08:00", "closes": "24:00"}, {"weekday": "mon", "opens": "06:30", "closes": "22:00"}]},
    )
    got = client.get(f"/v1/admin/garages/{garage_id}/opening-hours")

    assert put.status_code == 200
    assert got.json()["days"] == [
        {"weekday": "mon", "opens": "06:30", "closes": "22:00"},
        {"weekday": "sat", "opens": "08:00", "closes": "24:00"},
    ]


def test_opening_hours_closing_before_opening_returns_422(client: TestClient) -> None:
    garage_id = _garage(client, _operator(client), spots=0)

    resp = client.put(
        f"/v1/admin/garages/{garage_id}/opening-hours",
        json={"days": [{"weekday": "mon", "opens": "22:00", "closes": "06:00"}]},
    )

    assert resp.status_code == 422


# --- spots -----------------------------------------------------------------


def test_spot_types_are_listed(client: TestClient) -> None:
    codes = [t["code"] for t in client.get("/v1/admin/spot-types").json()]

    assert "ev" in codes and "standard" in codes


def test_spots_are_created_with_normalized_codes(client: TestClient) -> None:
    garage_id = _garage(client, _operator(client), spots=0)

    resp = client.post(
        f"/v1/admin/garages/{garage_id}/spots",
        json={"spots": [{"code": "b 12", "spot_type": "ev", "level": "L2"}]},
    )

    assert resp.status_code == 201
    assert resp.json()[0]["code"] == "B-12"
    assert resp.json()[0]["spot_type"] == "ev"


def test_duplicate_spot_code_returns_409(client: TestClient) -> None:
    garage_id = _garage(client, _operator(client), spots=2)

    resp = client.post(f"/v1/admin/garages/{garage_id}/spots", json={"spots": [{"code": "A1"}]})

    assert resp.status_code == 409


def test_unknown_spot_type_returns_422(client: TestClient) -> None:
    garage_id = _garage(client, _operator(client), spots=0)

    resp = client.post(f"/v1/admin/garages/{garage_id}/spots", json={"spots": [{"code": "Z1", "spot_type": "boat"}]})

    assert resp.status_code == 422


def test_spot_with_upcoming_reservation_cannot_be_deactivated(client: TestClient) -> None:
    garage_id = _garage(client, _operator(client), spots=1)
    (spot,) = client.get(f"/v1/admin/garages/{garage_id}/spots").json()
    _reserve(client, garage_id, "2099-01-01T10:00:00Z", "2099-01-01T12:00:00Z")

    resp = client.patch(f"/v1/admin/spots/{spot['spot_id']}", json={"is_active": False})

    assert resp.status_code == 409


def test_free_spot_can_be_deactivated_and_is_hidden(client: TestClient) -> None:
    garage_id = _garage(client, _operator(client), spots=2)
    first, _ = client.get(f"/v1/admin/garages/{garage_id}/spots").json()

    resp = client.patch(f"/v1/admin/spots/{first['spot_id']}", json={"is_active": False})

    assert resp.status_code == 200
    assert resp.json()["is_active"] is False
    assert len(client.get(f"/v1/admin/garages/{garage_id}/spots").json()) == 1
    assert client.get("/v1/admin/spots/999").status_code == 404


# --- tariffs and quotes ----------------------------------------------------


def test_tariff_create_get_and_close(client: TestClient) -> None:
    garage_id = _garage(client, _operator(client), spots=0)
    tariff = _flat_tariff(client, garage_id)

    assert tariff["currency"] == "EUR"
    assert tariff["bands"][0]["weekdays"] == ALL_DAYS
    assert client.get(f"/v1/admin/tariffs/{tariff['tariff_id']}").json()["bands"] == tariff["bands"]
    closed = client.post(f"/v1/admin/tariffs/{tariff['tariff_id']}/close", json={"valid_to": "2026-12-01"})
    assert closed.json()["valid_to"] == "2026-12-01"
    assert len(client.get(f"/v1/admin/garages/{garage_id}/tariffs").json()) == 1


def test_tariff_with_uncovered_hours_returns_422(client: TestClient) -> None:
    garage_id = _garage(client, _operator(client), spots=0)

    resp = client.post(
        f"/v1/admin/garages/{garage_id}/tariffs",
        json={
            "name": "Daytime only",
            "currency": "EUR",
            "valid_from": "2026-01-01",
            "bands": [{"weekdays": ALL_DAYS, "starts": "08:00", "ends": "20:00", "rate_cents_per_block": 100}],
        },
    )

    assert resp.status_code == 422


def test_overlapping_tariff_returns_409(client: TestClient) -> None:
    garage_id = _garage(client, _operator(client), spots=0)
    _flat_tariff(client, garage_id)

    resp = client.post(
        f"/v1/admin/garages/{garage_id}/tariffs",
        json={
            "name": "Again",
            "currency": "EUR",
            "valid_from": "2026-06-01",
            "bands": [{"weekdays": ALL_DAYS, "starts": "00:00", "ends": "24:00", "rate_cents_per_block": 50}],
        },
    )

    assert resp.status_code == 409


def test_quote_for_two_hours_and_fetch_it_back(client: TestClient) -> None:
    garage_id = _garage(client, _operator(client), spots=0)
    _flat_tariff(client, garage_id, rate=100)

    created = client.post(
        f"/v1/garages/{garage_id}/quotes",
        json={"window_start": "2026-08-15T10:00:00Z", "window_end": "2026-08-15T12:00:00Z"},
    )
    fetched = client.get(f"/v1/quotes/{created.json()['quote_id']}")

    assert created.status_code == 201
    body = created.json()
    assert body["amount_cents"] == 800
    assert body["currency"] == "EUR"
    assert body["breakdown"]["lines"][0]["blocks"] == 8
    assert fetched.status_code == 200
    assert fetched.json()["amount_cents"] == 800
    assert fetched.json()["expired"] is False


def test_quote_without_a_tariff_returns_422(client: TestClient) -> None:
    garage_id = _garage(client, _operator(client), spots=0)

    resp = client.post(
        f"/v1/garages/{garage_id}/quotes",
        json={"window_start": "2026-08-15T10:00:00Z", "window_end": "2026-08-15T12:00:00Z"},
    )

    assert resp.status_code == 422


def test_quote_errors(client: TestClient) -> None:
    garage_id = _garage(client, _operator(client), spots=0)
    _flat_tariff(client, garage_id)

    backwards = client.post(
        f"/v1/garages/{garage_id}/quotes",
        json={"window_start": "2026-08-15T12:00:00Z", "window_end": "2026-08-15T10:00:00Z"},
    )
    too_long = client.post(
        f"/v1/garages/{garage_id}/quotes",
        json={"window_start": "2026-08-01T00:00:00Z", "window_end": "2026-10-01T00:00:00Z"},
    )
    unknown_garage = client.post(
        "/v1/garages/999/quotes",
        json={"window_start": "2026-08-15T10:00:00Z", "window_end": "2026-08-15T12:00:00Z"},
    )

    assert backwards.status_code == 422
    assert too_long.status_code == 422
    assert unknown_garage.status_code == 404
    assert client.get("/v1/quotes/00000000-0000-0000-0000-000000000001").status_code == 404


def test_settlement_endpoint_charges_completed_reservations(client: TestClient) -> None:
    garage_id = _garage(client, _operator(client), spots=1)
    _flat_tariff(client, garage_id, rate=100)
    public_id = _reserve(client, garage_id, "2026-08-15T10:00:00Z", "2026-08-15T12:00:00Z")
    client.post(f"/v1/reservations/{public_id}/check-in")
    client.post(f"/v1/reservations/{public_id}/complete")

    assert client.get(f"/v1/reservations/{public_id}/charge").status_code == 404
    assert client.post("/internal/pricing/settle").status_code == 403
    result = client.post("/internal/pricing/settle", headers=INTERNAL)

    assert result.status_code == 200
    assert result.json() == {"claimed": 1, "settled": 1, "unpriced": 0, "already_settled": 0}
    charge = client.get(f"/v1/reservations/{public_id}/charge")
    assert charge.status_code == 200
    assert charge.json()["currency"] == "EUR"
    assert charge.json()["amount_cents"] > 0


# --- drivers and vehicles --------------------------------------------------


def test_driver_registration_and_update(client: TestClient) -> None:
    created = client.post(
        "/v1/drivers",
        json={"driver_id": 42, "display_name": "  Ana   de Vries ", "email": "Ana@Example.COM", "phone": "+31 6 1234 5678"},
    )
    patched = client.patch("/v1/drivers/42", json={"email": "", "notify_reminders": False})

    assert created.status_code == 201
    assert created.json()["display_name"] == "Ana de Vries"
    assert created.json()["email"] == "Ana@example.com"
    assert created.json()["phone"] == "+31612345678"
    assert patched.status_code == 200
    assert patched.json()["email"] is None
    assert patched.json()["notify_reminders"] is False


def test_driver_errors(client: TestClient) -> None:
    no_contact = client.post("/v1/drivers", json={"driver_id": 1, "display_name": "Bo"})
    client.post("/v1/drivers", json={"driver_id": 2, "display_name": "Cy", "email": "cy@example.com"})
    twice = client.post("/v1/drivers", json={"driver_id": 2, "display_name": "Cy", "email": "cy2@example.com"})
    clear_last_contact = client.patch("/v1/drivers/2", json={"email": ""})

    assert no_contact.status_code == 422
    assert twice.status_code == 409
    assert clear_last_contact.status_code == 422
    assert client.get("/v1/drivers/999").status_code == 404


def test_vehicle_lifecycle(client: TestClient) -> None:
    client.post("/v1/drivers", json={"driver_id": 42, "display_name": "Ana", "email": "ana@example.com"})

    first = client.post("/v1/drivers/42/vehicles", json={"country_code": "fr", "plate": "ab-123-cd"})
    second = client.post("/v1/drivers/42/vehicles", json={"country_code": "NL", "plate": "12ABC3", "nickname": "Van"})
    duplicate = client.post("/v1/drivers/42/vehicles", json={"country_code": "FR", "plate": "AB 123 CD"})
    bad_plate = client.post("/v1/drivers/42/vehicles", json={"country_code": "FR", "plate": "ZZZZ"})

    assert first.status_code == 201
    assert first.json()["plate"] == "AB123CD"
    assert first.json()["is_default"] is True
    assert duplicate.status_code == 409
    assert bad_plate.status_code == 422

    second_id = second.json()["vehicle_id"]
    made_default = client.post(f"/v1/drivers/42/vehicles/{second_id}/default")
    assert made_default.json()["is_default"] is True

    removed = client.delete(f"/v1/drivers/42/vehicles/{second_id}")
    assert removed.status_code == 204
    remaining = client.get("/v1/drivers/42/vehicles").json()
    assert [(v["plate"], v["is_default"]) for v in remaining] == [("AB123CD", True)]
    assert client.delete(f"/v1/drivers/42/vehicles/{second_id}").status_code == 404


def test_vehicle_limit_returns_409(client: TestClient) -> None:
    client.post("/v1/drivers", json={"driver_id": 42, "display_name": "Ana", "email": "ana@example.com"})
    for n in range(5):
        resp = client.post("/v1/drivers/42/vehicles", json={"country_code": "US", "plate": f"CAR{n}"})
        assert resp.status_code == 201

    resp = client.post("/v1/drivers/42/vehicles", json={"country_code": "US", "plate": "CAR9"})

    assert resp.status_code == 409


# --- reports ---------------------------------------------------------------


def test_occupancy_report_fills_every_day(client: TestClient) -> None:
    garage_id = _garage(client, _operator(client), spots=2)
    _reserve(client, garage_id, "2026-08-15T10:00:00Z", "2026-08-15T22:00:00Z")

    resp = client.get(
        f"/v1/admin/garages/{garage_id}/reports/occupancy", params={"from": "2026-08-14", "to": "2026-08-16"}
    )

    assert resp.status_code == 200
    days = resp.json()["days"]
    assert [d["date"] for d in days] == ["2026-08-14", "2026-08-15", "2026-08-16"]
    assert [d["occupied_minutes"] for d in days] == [0, 720, 0]
    assert days[1]["capacity_minutes"] == 2 * 1440
    assert days[1]["occupancy_ratio"] == 0.25


def test_report_range_errors(client: TestClient) -> None:
    garage_id = _garage(client, _operator(client), spots=0)

    backwards = client.get(
        f"/v1/admin/garages/{garage_id}/reports/occupancy", params={"from": "2026-08-16", "to": "2026-08-14"}
    )
    too_long = client.get(
        f"/v1/admin/garages/{garage_id}/reports/status", params={"from": "2026-01-01", "to": "2026-12-31"}
    )

    assert backwards.status_code == 422
    assert too_long.status_code == 422
    assert client.get("/v1/admin/garages/999/reports/status", params={"from": "2026-08-14", "to": "2026-08-14"}).status_code == 404


def test_status_report_counts_and_cancellation_rate(client: TestClient) -> None:
    garage_id = _garage(client, _operator(client), spots=2)
    kept = _reserve(client, garage_id, "2026-08-15T10:00:00Z", "2026-08-15T12:00:00Z")
    dropped = _reserve(client, garage_id, "2026-08-15T10:00:00Z", "2026-08-15T12:00:00Z", driver_id=7)
    client.post(f"/v1/reservations/{dropped}/cancel")

    resp = client.get(
        f"/v1/admin/garages/{garage_id}/reports/status", params={"from": "2026-08-15", "to": "2026-08-15"}
    )

    assert resp.json()["counts"] == {"cancelled": 1, "reserved": 1}
    assert resp.json()["cancellation_rate"] == 0.5
    assert kept


def test_revenue_report_after_settlement(client: TestClient) -> None:
    operator_id = _operator(client)
    garage_id = _garage(client, operator_id, spots=1)
    _flat_tariff(client, garage_id)
    public_id = _reserve(client, garage_id, "2026-08-15T10:00:00Z", "2026-08-15T12:00:00Z")
    client.post(f"/v1/reservations/{public_id}/check-in")
    client.post(f"/v1/reservations/{public_id}/complete")
    client.post("/internal/pricing/settle", headers=INTERNAL)
    charged = client.get(f"/v1/reservations/{public_id}/charge").json()["amount_cents"]

    resp = client.get(
        f"/v1/admin/operators/{operator_id}/reports/revenue", params={"from": "2026-08-15", "to": "2026-08-15"}
    )

    assert resp.status_code == 200
    body = resp.json()
    assert body["totals_by_currency"] == {"EUR": charged}
    assert [(g["garage_id"], g["garage_name"], g["charges"]) for g in body["garages"]] == [(garage_id, "Downtown", 1)]


# --- internal notification endpoints ----------------------------------------


def test_notification_endpoints_require_the_internal_token(client: TestClient) -> None:
    assert client.post("/internal/notifications/schedule-reminders").status_code == 403
    assert client.post("/internal/notifications/dispatch").status_code == 403


def test_reminder_is_scheduled_and_dispatched(client: TestClient) -> None:
    from datetime import UTC, datetime, timedelta

    garage_id = _garage(client, _operator(client), spots=1)
    client.post("/v1/drivers", json={"driver_id": 42, "display_name": "Ana", "email": "ana@example.com"})
    start = (datetime.now(UTC) + timedelta(minutes=30)).replace(microsecond=0)
    _reserve(client, garage_id, start.isoformat(), (start + timedelta(hours=1)).isoformat())

    scheduled = client.post("/internal/notifications/schedule-reminders", headers=INTERNAL)
    dispatched = client.post("/internal/notifications/dispatch", headers=INTERNAL)
    again = client.post("/internal/notifications/dispatch", headers=INTERNAL)

    assert scheduled.json() == {"scheduled": 1}
    assert dispatched.json() == {"claimed": 1, "sent": 1, "skipped": 0, "failed": 0}
    assert again.json()["claimed"] == 0
