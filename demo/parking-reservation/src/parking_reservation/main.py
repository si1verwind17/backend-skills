import os

from fastapi import FastAPI

from parking_reservation.sys.google_scheduler_verifier import GoogleSchedulerVerifier
from parking_reservation.sys.logging_setup import configure_logging
from parking_reservation.sys.pubsub_event_publisher import PubSubEventPublisher
from parking_reservation.sys.settings import load_settings
from parking_reservation.sys.wiring import build_app


def create_app_from_env() -> FastAPI:
    """uvicorn --factory entry point; a bad configuration raises here, so the deploy fails at boot."""
    configure_logging()
    settings = load_settings(os.environ)
    verifier = GoogleSchedulerVerifier(settings.relay_audience, settings.scheduler_service_account)
    return build_app(settings, PubSubEventPublisher(settings.gcp_project), verifier)
