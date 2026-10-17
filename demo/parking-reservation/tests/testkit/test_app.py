from fastapi import FastAPI

from parking_reservation.core.event_publisher import EventPublisher
from parking_reservation.sys.settings import Settings
from parking_reservation.sys.wiring import build_app
from testkit.fake_event_publisher import FakeEventPublisher
from testkit.fake_relay_verifier import FakeRelayVerifier

IDENTITY_HEADER = "x-claims"


def settings_for(database_url: str) -> Settings:
    return Settings(
        database_url=database_url,
        identity_header=IDENTITY_HEADER,
        gcp_project="proj",
        scheduler_service_account="scheduler@proj.iam.gserviceaccount.com",
        relay_audience="https://svc",
    )


def build_test_app(database_url: str, publisher: EventPublisher | None = None) -> FastAPI:
    """The real composition root with the broker and the token check swapped for fakes."""
    return build_app(settings_for(database_url), publisher or FakeEventPublisher(), FakeRelayVerifier())
