from fastapi import FastAPI

from parking_reservation.api.app_factory import create_app
from parking_reservation.api.caller_reader import CallerReader
from parking_reservation.core.event_publisher import EventPublisher
from parking_reservation.core.relay_caller_verifier import RelayCallerVerifier
from parking_reservation.repo.postgres_garage_repo import PostgresGarageRepo
from parking_reservation.repo.postgres_health_check import PostgresHealthCheck
from parking_reservation.repo.postgres_outbox_repo import PostgresOutboxRepo
from parking_reservation.repo.postgres_reservation_repo import PostgresReservationRepo
from parking_reservation.services.day_lookup_service import DayLookupService
from parking_reservation.services.relay_service import RelayService
from parking_reservation.services.reservation_service import ReservationService
from parking_reservation.sys.database import open_pool
from parking_reservation.sys.settings import Settings
from parking_reservation.sys.system_clock import SystemClock
from parking_reservation.sys.uuid7_id_source import Uuid7IdSource


def build_app(settings: Settings, publisher: EventPublisher, relay_verifier: RelayCallerVerifier) -> FastAPI:
    """Composition root: the only place that knows every concrete class.

    The broker publisher and the token verifier are passed in so tests can swap them (own interfaces).
    """
    pool = open_pool(settings.database_url)

    def shutdown() -> None:
        publisher.close()
        pool.close()

    reservation_repo = PostgresReservationRepo(pool)
    return create_app(
        reservations=ReservationService(reservation_repo, SystemClock(), Uuid7IdSource()),
        day_lookup=DayLookupService(PostgresGarageRepo(pool), reservation_repo),
        relay=RelayService(PostgresOutboxRepo(pool), publisher, SystemClock()),
        relay_verifier=relay_verifier,
        callers=CallerReader(settings.identity_header),
        check_database=PostgresHealthCheck(pool).check,
        on_shutdown=shutdown,
    )
