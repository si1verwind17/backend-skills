"""The boundary owns outcome logging: one line per request, unexpected failures included."""

import logging
from datetime import timedelta

import pytest
from fastapi.testclient import TestClient

from parking_reservation.api.app import create_app
from tests.stubbed.fakes import FakeGarageStore, FakeReservationStore
from tests.stubbed.wiring import build_services
from tests.support import NOW, SETTINGS, FakeVerifier

HEADERS = {
    "Authorization": "Bearer fe-token",
    "X-Actor-Id": "drv",
    "X-Actor-Role": "driver",
    "Idempotency-Key": "k",
}
BODY = {
    "garage_id": 5,
    "window_start": (NOW + timedelta(hours=1)).isoformat(),
    "window_end": (NOW + timedelta(hours=2)).isoformat(),
}


class Exploding(FakeReservationStore):
    def find_by_key(self, driver_id, idempotency_key):  # type: ignore[no-untyped-def]
        raise RuntimeError("defect")


def client_for(store: FakeReservationStore) -> TestClient:
    services = build_services(store, FakeGarageStore({5}))
    return TestClient(create_app(SETTINGS, services, FakeVerifier()), raise_server_exceptions=False)


def outcomes(caplog: pytest.LogCaptureFixture) -> list[logging.LogRecord]:
    return [r for r in caplog.records if r.name == "parking_reservation.api"]


def test_an_unexpected_failure_is_one_error_line_and_a_retryable_503(
    caplog: pytest.LogCaptureFixture,
) -> None:
    caplog.set_level(logging.INFO)
    response = client_for(Exploding()).post("/v1/reservations", json=BODY, headers=HEADERS)
    assert response.status_code == 503 and response.json()["code"] == "UNAVAILABLE"
    lines = outcomes(caplog)
    assert len(lines) == 1 and lines[0].levelno == logging.ERROR and lines[0].exc_info
    assert "garage=5" in lines[0].getMessage()


def test_expected_rejections_are_one_warning_with_the_garage(
    caplog: pytest.LogCaptureFixture,
) -> None:
    caplog.set_level(logging.INFO)
    response = client_for(FakeReservationStore()).post(
        "/v1/reservations", json=BODY, headers=HEADERS
    )
    assert response.status_code == 409
    lines = outcomes(caplog)
    assert len(lines) == 1 and lines[0].levelno == logging.WARNING
    assert "code=GARAGE_FULL" in lines[0].getMessage() and "garage=5" in lines[0].getMessage()


def test_a_rejected_token_is_logged_too(caplog: pytest.LogCaptureFixture) -> None:
    caplog.set_level(logging.INFO)
    client_for(FakeReservationStore()).get(
        "/v1/reservations/x", headers={"Authorization": "Bearer nope"}
    )
    lines = outcomes(caplog)
    assert len(lines) == 1 and "status=401" in lines[0].getMessage()


def test_health_is_logged_at_info(caplog: pytest.LogCaptureFixture) -> None:
    caplog.set_level(logging.INFO)
    client_for(FakeReservationStore()).get("/health")
    assert outcomes(caplog)[0].levelno == logging.INFO
