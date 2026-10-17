import logging

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from psycopg import errors

from parking_reservation.api.app_factory import create_app
from parking_reservation.api.caller_reader import CallerReader
from parking_reservation.core.defect_error import DefectError
from parking_reservation.services.day_lookup_service import DayLookupService
from parking_reservation.services.relay_service import RelayService
from parking_reservation.services.reservation_service import ReservationService
from testkit.fake_clock import FakeClock
from testkit.fake_event_publisher import FakeEventPublisher
from testkit.fake_relay_verifier import FakeRelayVerifier
from testkit.sequential_id_source import SequentialIdSource
from testkit.stub_garage_repo import StubGarageRepo
from testkit.stub_outbox_repo import StubOutboxRepo
from testkit.stub_reservation_repo import StubReservationRepo


def _client(check) -> TestClient:
    service = ReservationService(StubReservationRepo(), FakeClock(), SequentialIdSource())
    lookup = DayLookupService(StubGarageRepo({}), StubReservationRepo())
    relay = RelayService(StubOutboxRepo([]), FakeEventPublisher(), FakeClock())
    app: FastAPI = create_app(
        service, lookup, relay, FakeRelayVerifier(), CallerReader("x-claims"), check, lambda: None
    )
    return TestClient(app, raise_server_exceptions=False)


def _raise(error: Exception):
    def check() -> None:
        raise error

    return check


@pytest.mark.parametrize(
    "error", [errors.UniqueViolation("x"), errors.DataError("x"), errors.OperationalError("x")]
)
def test_any_database_error_is_a_json_503(error: Exception) -> None:
    response = _client(_raise(error)).get("/healthz")
    assert response.status_code == 503
    assert response.json()["code"] == "UNAVAILABLE"


def test_a_defect_is_a_json_500_and_logged_exactly_once(caplog: pytest.LogCaptureFixture) -> None:
    with caplog.at_level(logging.INFO):
        response = _client(_raise(DefectError("boom"))).get("/healthz")
    assert response.status_code == 500
    assert response.json() == {"code": "INTERNAL_ERROR", "message": "internal error"}
    failures = [r for r in caplog.records if r.levelno >= logging.ERROR]
    assert len(failures) == 1 and failures[0].exc_info is not None


def test_unknown_routes_and_methods_use_the_error_body() -> None:
    client = _client(lambda: None)
    assert client.get("/nope").json()["code"] == "HTTP_404"
    assert client.get("/v1/reservations").json()["code"] == "HTTP_405"


def test_the_openapi_document_describes_create_as_201_with_typed_errors() -> None:
    spec = _client(lambda: None).get("/openapi.json").json()
    responses = spec["paths"]["/v1/reservations"]["post"]["responses"]
    assert {"200", "201", "401", "404", "409", "422", "503"} <= set(responses)
    assert "HTTPValidationError" not in str(responses["422"])


def test_the_log_line_names_the_kind_of_database_error(caplog: pytest.LogCaptureFixture) -> None:
    with caplog.at_level(logging.INFO):
        _client(_raise(errors.UndefinedColumn("x"))).get("/healthz")
    fields = [r.__dict__["fields"] for r in caplog.records if r.name == "parking_reservation.request"][0]
    assert fields["database_error"].startswith("UndefinedColumn")
