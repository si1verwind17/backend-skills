"""What the business layer needs from the outside world, stated as interfaces."""

from collections.abc import Callable
from datetime import date, datetime
from typing import Any, Protocol
from uuid import UUID

from parking_reservation.domain.outbox import OutboxEvent, Settled, Settlement
from parking_reservation.domain.reservation import Reservation


class Clock(Protocol):
    def now(self) -> datetime: ...


class IdGenerator(Protocol):
    def new_id(self) -> UUID: ...


class ReservationStore(Protocol):
    def find_by_key(self, driver_id: str, idempotency_key: str) -> Reservation | None: ...

    def book(
        self,
        *,
        public_id: UUID,
        event_id: UUID,
        driver_id: str,
        idempotency_key: str,
        garage_id: int,
        window_start: datetime,
        window_end: datetime,
        now: datetime,
    ) -> Reservation | None:
        """Book the lowest free active spot, or return None when no row was created."""
        ...

    def get_for_driver(self, public_id: UUID, driver_id: str) -> Reservation | None: ...

    def check_in(
        self, public_id: UUID, driver_id: str, event_id: UUID, now: datetime
    ) -> Reservation | None:
        """BOOKED to CHECKED_IN inside the window, or None when no row matched (W2)."""
        ...

    def check_out(
        self, public_id: UUID, driver_id: str, event_id: UUID, now: datetime
    ) -> Reservation | None:
        """CHECKED_IN to COMPLETED, or None when no row matched (W3)."""
        ...

    def cancel(
        self, public_id: UUID, driver_id: str, event_id: UUID, now: datetime
    ) -> Reservation | None:
        """BOOKED to CANCELLED, or None when no row matched (W4)."""
        ...

    def list_for_garage_day(self, garage_id: int, day: date) -> list[Reservation] | None:
        """Reservations overlapping the garage-local day, or None for an unknown garage."""
        ...


class GarageStore(Protocol):
    def exists(self, garage_id: int) -> bool: ...


class StoreUnavailableError(Exception):
    """The database could not answer in time or at all. The caller may repeat the request."""


class TokenRejectedError(Exception):
    """The token is missing, malformed, expired, for another audience or unsigned."""


class TokenVerifierUnavailableError(Exception):
    """Google's public keys could not be fetched, so no token can be judged."""


class TokenVerifier(Protocol):
    def verify(self, token: str, audience: str) -> str:
        """Return the verified email of the token's service account."""
        ...


class PublishRejectedError(Exception):
    """The broker rejected this one event as invalid or oversize; repeating cannot help."""


class PublishFailedError(Exception):
    """The publish failed for a reason that may pass: broker, topic, permission, timeout."""


class EventPublisher(Protocol):
    def publish(self, topic: str, payload: dict[str, Any], event: OutboxEvent) -> None:
        """Publish and wait for the broker's answer; raise PublishRejectedError or
        PublishFailedError otherwise."""
        ...


class OutboxStore(Protocol):
    def settle_next(
        self, now: datetime, settle: Callable[[OutboxEvent], Settlement]
    ) -> Settled | None:
        """Claim one due pending row, let `settle` decide, record it and commit.

        Returns None when no row is due. `settle` runs inside the claim's transaction and
        must not raise for publish outcomes.
        """
        ...

    def stuck_event_ids(self, attempts_at_least: int) -> list[UUID]:
        """Pending rows that have failed to publish at least that many times."""
        ...
