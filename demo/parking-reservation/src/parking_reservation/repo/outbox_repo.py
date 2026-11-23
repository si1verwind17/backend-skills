"""Postgres implementation of the outbox store (W5, AP6)."""

from collections.abc import Callable
from datetime import datetime
from uuid import UUID

from parking_reservation.domain.outbox import (
    OutboxEvent,
    Parked,
    Published,
    RetryLater,
    Settled,
    Settlement,
)
from parking_reservation.repo import sql
from parking_reservation.repo.database import Pool
from parking_reservation.repo.retry import read_with_retry
from parking_reservation.repo.store_errors import store_errors

MAX_ERROR_LENGTH = 500


class OutboxRepo:
    def __init__(self, pool: Pool) -> None:
        self._pool = pool

    def settle_next(
        self, now: datetime, settle: Callable[[OutboxEvent], Settlement]
    ) -> Settled | None:
        """One short transaction: claim a due row `SKIP LOCKED`, settle it, commit."""
        with store_errors(), self._pool.connection() as conn:
            row = conn.execute(sql.load("claim_outbox"), {"now": now}).fetchone()
            if row is None:
                return None
            event = OutboxEvent(
                outbox_id=row["outbox_id"],
                event_id=row["event_id"],
                event_type=row["event_type"],
                payload=row["payload"],
                attempts=row["attempts"],
            )
            settlement = settle(event)
            statement, params = self._record(event, settlement, now)
            conn.execute(statement, params)
            return Settled(event, settlement)

    def stuck_event_ids(self, attempts_at_least: int) -> list[UUID]:
        return read_with_retry(lambda: self._stuck(attempts_at_least))

    def _stuck(self, attempts_at_least: int) -> list[UUID]:
        with self._pool.connection() as conn:
            rows = conn.execute(
                sql.load("stuck_outbox"), {"attempts": attempts_at_least}
            ).fetchall()
        return [row["event_id"] for row in rows]

    @staticmethod
    def _record(
        event: OutboxEvent, settlement: Settlement, now: datetime
    ) -> tuple[str, dict[str, object]]:
        base: dict[str, object] = {"outbox_id": event.outbox_id, "now": now}
        match settlement:
            case Published():
                return sql.load("mark_published"), base
            case RetryLater(error, next_attempt_at):
                return sql.load("mark_retry"), base | {
                    "error": error[:MAX_ERROR_LENGTH],
                    "next_attempt_at": next_attempt_at,
                }
            case Parked(error):
                return sql.load("mark_parked"), base | {"error": error[:MAX_ERROR_LENGTH]}
