"""The composition root refuses to start on bad configuration."""

import pytest

from parking_reservation.config import ConfigError
from parking_reservation.main import build_app


@pytest.mark.parametrize("missing", ["DATABASE_URL", "AUTH_AUDIENCE", "SCHEDULER_SERVICE_ACCOUNT"])
def test_startup_stops_when_a_setting_is_missing_or_empty(
    monkeypatch: pytest.MonkeyPatch, missing: str
) -> None:
    good = {
        "DATABASE_URL": "postgresql://u:p@127.0.0.1:1/x",
        "GCP_PROJECT": "my-project",
        "AUTH_AUDIENCE": "https://svc",
        "FRONT_END_SERVICE_ACCOUNT": "fe@x",
        "SCHEDULER_SERVICE_ACCOUNT": "sc@x",
    }
    for name, value in good.items():
        monkeypatch.setenv(name, value)
    monkeypatch.setenv("PUBSUB_EMULATOR_HOST", "127.0.0.1:1")
    monkeypatch.setenv(missing, "")
    with pytest.raises(ConfigError, match=missing):
        build_app()


def test_a_complete_environment_builds_the_app(monkeypatch: pytest.MonkeyPatch) -> None:
    for name, value in {
        "DATABASE_URL": "postgresql://u:p@127.0.0.1:1/x",
        "GCP_PROJECT": "my-project",
        "AUTH_AUDIENCE": "https://svc",
        "FRONT_END_SERVICE_ACCOUNT": "fe@x",
        "SCHEDULER_SERVICE_ACCOUNT": "sc@x",
        "PUBSUB_EMULATOR_HOST": "127.0.0.1:1",
    }.items():
        monkeypatch.setenv(name, value)
    assert build_app().title == "parking-reservation"


def test_startup_stops_when_pubsub_credentials_are_unusable(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import google.auth
    import google.auth.exceptions

    def no_credentials(*args: object, **kwargs: object) -> None:
        raise google.auth.exceptions.DefaultCredentialsError("none")

    for name, value in {
        "DATABASE_URL": "postgresql://u:p@127.0.0.1:1/x",
        "GCP_PROJECT": "my-project",
        "AUTH_AUDIENCE": "https://svc",
        "FRONT_END_SERVICE_ACCOUNT": "fe@x",
        "SCHEDULER_SERVICE_ACCOUNT": "sc@x",
    }.items():
        monkeypatch.setenv(name, value)
    monkeypatch.delenv("PUBSUB_EMULATOR_HOST", raising=False)
    monkeypatch.setattr(google.auth, "default", no_credentials)
    with pytest.raises(google.auth.exceptions.DefaultCredentialsError):
        build_app()
