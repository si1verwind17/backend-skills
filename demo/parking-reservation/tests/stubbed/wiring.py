"""Builds the full service set over in-memory stores."""

from parking_reservation.api.app import Services
from parking_reservation.domain.ports import (
    Clock,
    EventPublisher,
    GarageStore,
    IdGenerator,
    OutboxStore,
    ReservationStore,
)
from parking_reservation.service.lookup_service import LookupService
from parking_reservation.service.relay_service import RelayService
from parking_reservation.service.reserve_service import ReserveService
from parking_reservation.service.transition_service import TransitionService
from parking_reservation.service.view_service import ViewService
from tests.stubbed.fakes_outbox import FakeOutboxStore, FakePublisher
from tests.support import FakeClock, RandomIds


def build_services(
    store: ReservationStore,
    garages: GarageStore,
    clock: Clock | None = None,
    ids: IdGenerator | None = None,
    outbox: OutboxStore | None = None,
    publisher: EventPublisher | None = None,
) -> Services:
    clock = clock or FakeClock()
    ids = ids or RandomIds()
    return Services(
        reserve=ReserveService(store, garages, clock, ids),
        view=ViewService(store),
        transitions=TransitionService(store, clock, ids),
        lookup=LookupService(store),
        relay=RelayService(outbox or FakeOutboxStore([]), publisher or FakePublisher(), clock),
    )
