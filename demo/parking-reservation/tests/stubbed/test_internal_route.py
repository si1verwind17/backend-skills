"""The scheduler's endpoint and who may call it (AD6, AD7)."""

import logging

import pytest
from fastapi.testclient import TestClient

from parking_reservation.api.app import create_app
from tests.stubbed.fakes import FakeGarageStore, FakeReservationStore
from tests.stubbed.fakes_outbox import FakeOutboxStore, FakePublisher, event
from tests.stubbed.wiring import build_services
from tests.support import SETTINGS, FakeVerifier

SCHEDULER = {"Authorization": "Bearer sc-token"}
RELAY = "/internal/outbox/relay"


def client_for(outbox: FakeOutboxStore, publisher: FakePublisher | None = None) -> TestClient:
    services = build_services(
        FakeReservationStore(),
        FakeGarageStore(set()),
        outbox=outbox,
        publisher=publisher or FakePublisher(),
    )
    return TestClient(create_app(SETTINGS, services, FakeVerifier()), raise_server_exceptions=False)


def test_the_scheduler_triggers_a_sweep() -> None:
    client = client_for(FakeOutboxStore([event(), event("reserved")]))
    response = client.post(RELAY, headers=SCHEDULER)
    assert response.status_code == 200
    assert response.json() == {"published": 2, "retried": 0, "parked": 0, "stuck": 0}


@pytest.mark.parametrize("token", ["fe-token", "other-token"])
def test_nobody_but_the_scheduler_may_trigger_it(token: str) -> None:
    client = client_for(FakeOutboxStore([]))
    response = client.post(RELAY, headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 403 and response.json()["code"] == "FORBIDDEN"


def test_the_scheduler_may_not_use_v1() -> None:
    client = client_for(FakeOutboxStore([]))
    assert client.get("/v1/reservations/x", headers=SCHEDULER).status_code == 403


def test_the_endpoint_needs_a_token() -> None:
    assert client_for(FakeOutboxStore([])).post(RELAY).status_code == 401


def test_parked_and_stuck_events_are_logged_as_errors(caplog: pytest.LogCaptureFixture) -> None:
    publisher = FakePublisher()
    poison = event()
    publisher.reject(poison, "invalid")
    outbox = FakeOutboxStore([poison])
    outbox.stuck = [event().event_id]
    caplog.set_level(logging.INFO)
    response = client_for(outbox, publisher).post(RELAY, headers=SCHEDULER)
    assert response.json()["parked"] == 1 and response.json()["stuck"] == 1
    errors = [r.getMessage() for r in caplog.records if r.levelno == logging.ERROR]
    assert any(str(poison.event_id) in m and "reason=invalid" in m for m in errors)
    assert any(str(outbox.stuck[0]) in m for m in errors)


def test_a_store_failure_part_way_is_a_503_but_the_parked_row_is_still_logged(
    caplog: pytest.LogCaptureFixture,
) -> None:
    publisher = FakePublisher()
    poison = event()
    publisher.reject(poison, "oversize")
    outbox = FakeOutboxStore([poison, event()])
    outbox.fail_after = 1
    caplog.set_level(logging.INFO)
    response = client_for(outbox, publisher).post(RELAY, headers=SCHEDULER)
    assert response.status_code == 503 and response.json()["code"] == "UNAVAILABLE"
    errors = [r.getMessage() for r in caplog.records if r.levelno == logging.ERROR]
    assert any(str(poison.event_id) in m and "reason=oversize" in m for m in errors)
