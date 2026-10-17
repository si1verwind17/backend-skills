import base64
import json
from collections.abc import Iterator

import psycopg
import pytest
from fastapi.testclient import TestClient

from testkit.seed import reset_and_seed
from testkit.test_app import build_test_app

pytestmark = pytest.mark.integration

HEADER = "x-claims"


def _identity(sub: str, role: str | None = None) -> dict[str, str]:
    claims = {"sub": sub, **({"role": role} if role else {})}
    return {HEADER: base64.urlsafe_b64encode(json.dumps(claims).encode()).decode().rstrip("=")}


@pytest.fixture
def client(seeded: str) -> Iterator[TestClient]:
    with TestClient(build_test_app(seeded)) as c:
        yield c


def _book(
    client: TestClient, driver: str = "d1", garage: str = "G1", start: str = "2099-10-20T10:00:00Z"
) -> dict:
    end = start.replace("T10", "T12")
    response = client.post(
        "/v1/reservations",
        json={"garage_code": garage, "start_at": start, "end_at": end},
        headers={**_identity(driver), "Idempotency-Key": f"key-{driver}-{garage}-{start}"},
    )
    assert response.status_code == 201, response.text
    return response.json()


def _act(client: TestClient, rid: str, action: str, driver: str = "d1"):
    return client.post(f"/v1/reservations/{rid}/{action}", headers=_identity(driver))


def test_book_check_in_check_out_and_billing_event(client, seeded) -> None:
    rid = _book(client)["reservation_id"]
    assert _act(client, rid, "check-in").json()["status"] == "checked_in"
    again = _act(client, rid, "check-in")
    assert again.status_code == 200 and again.json()["status"] == "checked_in"
    done = _act(client, rid, "check-out")
    assert done.status_code == 200 and done.json()["status"] == "completed"
    assert done.json()["checked_out_at"] is not None
    assert _act(client, rid, "check-out").json() == done.json()
    with psycopg.connect(seeded) as conn:
        completed = conn.execute(
            "SELECT payload FROM outbox_event WHERE topic = 'parking-reservation-completed-v1'"
        ).fetchall()
    assert len(completed) == 1
    assert completed[0][0]["reservation_public_id"] == rid


@pytest.mark.parametrize(
    ("setup", "action"),
    [
        ([], "check-out"),
        (["check-in"], "cancel"),
        (["cancel"], "check-in"),
        (["cancel"], "check-out"),
        (["check-in", "check-out"], "cancel"),
        (["check-in", "check-out"], "check-in"),
    ],
)
def test_forbidden_transitions_are_409(client, setup, action) -> None:
    rid = _book(client)["reservation_id"]
    for step in setup:
        assert _act(client, rid, step).status_code == 200
    response = _act(client, rid, action)
    assert response.status_code == 409 and response.json()["code"] == "INVALID_TRANSITION"


def test_cancel_then_repeat_and_rebook(client) -> None:
    rid = _book(client, garage="G2")["reservation_id"]
    assert _act(client, rid, "cancel").json()["status"] == "cancelled"
    assert _act(client, rid, "cancel").status_code == 200
    assert _book(client, driver="d2", garage="G2")["spot_label"] == "B1"


def test_check_in_after_the_window_is_409_closed(client, seeded) -> None:
    rid = _book(client, start="2099-10-20T10:00:00Z")["reservation_id"]
    with psycopg.connect(seeded, autocommit=True) as conn:
        conn.execute(
            "UPDATE reservation SET start_at = '2020-01-01T10:00Z', end_at = '2020-01-01T12:00Z' "
            "WHERE public_id = %s",
            (rid,),
        )
    response = _act(client, rid, "check-in")
    assert response.status_code == 409 and response.json()["code"] == "CHECKIN_WINDOW_CLOSED"


def test_other_drivers_and_unknown_ids_are_404(client) -> None:
    rid = _book(client)["reservation_id"]
    for response in (
        _act(client, rid, "cancel", driver="intruder"),
        client.get(f"/v1/reservations/{rid}", headers=_identity("intruder")),
        _act(client, "00000000-0000-0000-0000-000000000000", "check-in"),
    ):
        assert response.status_code == 404 and response.json()["code"] == "RESERVATION_NOT_FOUND"
    assert client.get(f"/v1/reservations/{rid}", headers=_identity("d1")).json()["reservation_id"] == rid


def test_a_malformed_id_is_422(client) -> None:
    response = client.get("/v1/reservations/not-a-uuid", headers=_identity("d1"))
    assert response.status_code == 422 and response.json()["code"] == "INVALID_REQUEST"


def test_transitions_require_identity(client) -> None:
    rid = _book(client)["reservation_id"]
    assert client.post(f"/v1/reservations/{rid}/cancel").status_code == 401
    assert client.get(f"/v1/reservations/{rid}").status_code == 401


def test_staff_day_lookup_by_garage_and_garage_local_date(client, seeded) -> None:
    reset_and_seed(seeded, {"Z1": ("Europe/Zurich", ["S1", "S2"])})
    # 2026-10-20 in Zurich (CEST) is 2026-10-19T22:00Z .. 2026-10-20T22:00Z
    inside = _book(client, garage="Z1", start="2099-10-20T10:00:00Z")
    _book(client, driver="d2", garage="Z1", start="2099-10-21T10:00:00Z")
    staff = _identity("s1", "staff")
    response = client.get("/v1/garages/Z1/reservations?date=2099-10-20", headers=staff)
    assert response.status_code == 200
    assert [r["reservation_id"] for r in response.json()] == [inside["reservation_id"]]
    assert response.json()[0]["driver_id"] == "d1"
    cancelled = _act(client, inside["reservation_id"], "cancel")
    assert cancelled.status_code == 200
    day = client.get("/v1/garages/Z1/reservations?date=2099-10-20", headers=staff).json()
    assert [r["status"] for r in day] == ["cancelled"]
    assert client.get("/v1/garages/Z1/reservations?date=2099-10-25", headers=staff).json() == []


def test_staff_lookup_errors(client) -> None:
    staff = _identity("s1", "staff")
    assert (
        client.get("/v1/garages/NOPE/reservations?date=2099-10-20", headers=staff).json()["code"]
        == "GARAGE_NOT_FOUND"
    )
    assert (
        client.get("/v1/garages/G1/reservations?date=garbage", headers=staff).json()["code"]
        == "INVALID_REQUEST"
    )
    assert client.get("/v1/garages/G1/reservations", headers=staff).status_code == 422
    driver = client.get("/v1/garages/G1/reservations?date=2099-10-20", headers=_identity("d1"))
    assert driver.status_code == 403 and driver.json()["code"] == "FORBIDDEN"
    assert client.get("/v1/garages/G1/reservations?date=2099-10-20").status_code == 401


@pytest.mark.parametrize("day", ["9999-12-31", "0001-01-01", "1800-01-01"])
def test_dates_at_the_edge_of_the_calendar_are_422_not_500(client, day) -> None:
    response = client.get(f"/v1/garages/G1/reservations?date={day}", headers=_identity("s1", "staff"))
    assert response.status_code == 422 and response.json()["code"] == "INVALID_REQUEST"


def test_overlong_garage_codes_are_422(client) -> None:
    response = client.get(
        f"/v1/garages/{'G' * 65}/reservations?date=2099-10-20", headers=_identity("s1", "staff")
    )
    assert response.status_code == 422


def test_staff_cannot_act_as_drivers(client) -> None:
    response = client.post(
        "/v1/reservations",
        json={"garage_code": "G1", "start_at": "2099-10-20T10:00:00Z", "end_at": "2099-10-20T12:00:00Z"},
        headers={**_identity("s1", "staff"), "Idempotency-Key": "k"},
    )
    assert response.status_code == 403 and response.json()["code"] == "FORBIDDEN"


def test_failed_requests_still_log_the_reservation_id(client, caplog) -> None:
    import logging

    rid = _book(client)["reservation_id"]
    with caplog.at_level(logging.INFO, logger="parking_reservation.request"):
        response = _act(client, rid, "check-out")  # still reserved: 409
    assert response.status_code == 409
    fields = [r.__dict__["fields"] for r in caplog.records if r.name == "parking_reservation.request"]
    assert fields[-1]["reservation_id"] == rid and fields[-1]["error_code"] == "INVALID_TRANSITION"
