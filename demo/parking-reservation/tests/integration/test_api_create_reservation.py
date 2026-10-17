import base64
import json
from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient

from parking_reservation.sys.config_error import ConfigError
from testkit.test_app import build_test_app

pytestmark = pytest.mark.integration

HEADER = "x-claims"


def _identity(sub: str) -> dict[str, str]:
    raw = base64.urlsafe_b64encode(json.dumps({"sub": sub}).encode()).decode().rstrip("=")
    return {HEADER: raw}


@pytest.fixture
def client(seeded: str) -> Iterator[TestClient]:
    app = build_test_app(seeded)
    with TestClient(app) as c:
        yield c


def _body(
    start: str = "2099-10-20T10:00:00Z", end: str = "2099-10-20T12:00:00Z", garage: str = "G1"
) -> dict[str, str]:
    return {"garage_code": garage, "start_at": start, "end_at": end}


def _post(client: TestClient, body: dict[str, str], key: str = "k1", driver: str = "d1"):
    return client.post("/v1/reservations", json=body, headers={**_identity(driver), "Idempotency-Key": key})


def test_create_returns_201_then_200_for_the_same_key(client) -> None:
    first = _post(client, _body())
    again = _post(client, _body())
    assert (first.status_code, again.status_code) == (201, 200)
    assert first.json() == again.json()
    assert first.json()["status"] == "reserved" and first.json()["spot_label"] == "A1"
    assert first.json()["driver_id"] == "d1"


def test_no_spot_is_409(client) -> None:
    _post(client, _body(garage="G2"), key="a", driver="d1")
    other = _post(client, _body(garage="G2"), key="b", driver="d2")
    assert other.status_code == 409 and other.json()["code"] == "NO_SPOT_AVAILABLE"


def test_key_reuse_with_other_window_is_409(client) -> None:
    _post(client, _body())
    reused = _post(client, _body(end="2099-10-20T11:00:00Z"))
    assert reused.status_code == 409 and reused.json()["code"] == "IDEMPOTENCY_KEY_REUSED"


@pytest.mark.parametrize(
    "body",
    [
        _body(end="2099-10-20T10:00:00Z"),
        _body(end="2099-10-22T10:00:00Z"),
        _body(start="2001-01-01T00:00:00Z", end="2001-01-01T01:00:00Z"),
    ],
)
def test_bad_windows_are_422_invalid_window(client, body) -> None:
    response = _post(client, body)
    assert response.status_code == 422 and response.json()["code"] == "INVALID_WINDOW"


@pytest.mark.parametrize(
    "body", [{}, {"garage_code": "G1"}, _body(start="2099-10-20T10:00:00"), {**_body(), "extra": "x"}]
)
def test_malformed_bodies_are_422_invalid_request(client, body) -> None:
    response = _post(client, body)
    assert response.status_code == 422 and response.json()["code"] == "INVALID_REQUEST"


def test_missing_idempotency_key_is_422(client) -> None:
    response = client.post("/v1/reservations", json=_body(), headers=_identity("d1"))
    assert response.status_code == 422 and response.json()["code"] == "INVALID_REQUEST"


def test_unknown_garage_is_404(client) -> None:
    response = _post(client, _body(garage="NOPE"))
    assert response.status_code == 404 and response.json()["code"] == "GARAGE_NOT_FOUND"


def test_missing_identity_is_401_even_with_a_bad_body(client) -> None:
    response = client.post("/v1/reservations", json={}, headers={"Idempotency-Key": "k"})
    assert response.status_code == 401 and response.json()["code"] == "UNAUTHENTICATED"


def test_a_client_supplied_driver_header_does_not_authenticate(client) -> None:
    response = client.post(
        "/v1/reservations", json=_body(), headers={"X-Driver-Id": "d1", "Idempotency-Key": "k"}
    )
    assert response.status_code == 401


def test_healthz(client) -> None:
    assert client.get("/healthz").json() == {"status": "ok"}


def test_nul_characters_are_rejected_at_the_edge_not_a_500(client) -> None:
    response = _post(client, _body(garage="G1\u0000"))
    assert response.status_code == 422 and response.json()["code"] == "INVALID_REQUEST"
    nul_identity = client.post(
        "/v1/reservations", json=_body(), headers={**_identity("d\u0000"), "Idempotency-Key": "k"}
    )
    assert nul_identity.status_code == 401


def test_create_logs_one_line_with_the_reservation_id(client, caplog) -> None:
    import logging

    with caplog.at_level(logging.INFO, logger="parking_reservation.request"):
        response = _post(client, _body())
    lines = [r for r in caplog.records if r.name == "parking_reservation.request"]
    assert len(lines) == 1
    assert lines[0].fields["reservation_id"] == response.json()["reservation_id"]


REQUIRED_ENV = {
    "IDENTITY_HEADER": "x-claims",
    "GCP_PROJECT": "proj",
    "SCHEDULER_SERVICE_ACCOUNT": "scheduler@proj.iam.gserviceaccount.com",
    "RELAY_AUDIENCE": "https://svc",
}


@pytest.mark.parametrize("name", ["DATABASE_URL", *REQUIRED_ENV])
@pytest.mark.parametrize("broken", [None, " "])
def test_startup_entry_point_refuses_missing_or_blank_configuration(
    monkeypatch, seeded: str, restore_root_logging, name: str, broken: str | None
) -> None:
    from parking_reservation.main import create_app_from_env

    monkeypatch.setenv("DATABASE_URL", seeded)
    for key, value in REQUIRED_ENV.items():
        monkeypatch.setenv(key, value)
    if broken is None:
        monkeypatch.delenv(name)
    else:
        monkeypatch.setenv(name, broken)
    with pytest.raises(ConfigError):
        create_app_from_env()


def test_startup_entry_point_builds_the_real_app_from_a_complete_environment(
    monkeypatch, seeded: str, restore_root_logging
) -> None:
    from parking_reservation.main import create_app_from_env

    monkeypatch.setenv("DATABASE_URL", seeded)
    monkeypatch.setenv(
        "PUBSUB_EMULATOR_HOST", "127.0.0.1:1"
    )  # client needs no credentials; never contacted here
    for key, value in REQUIRED_ENV.items():
        monkeypatch.setenv(key, value)
    with TestClient(create_app_from_env()) as client:
        assert client.get("/healthz").status_code == 200
        assert client.post("/internal/relay").status_code == 401  # the real verifier rejects a missing token
