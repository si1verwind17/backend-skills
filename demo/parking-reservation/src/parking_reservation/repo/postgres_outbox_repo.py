from datetime import datetime
from uuid import UUID

from parking_reservation.core.outbox_event import OutboxEvent
from parking_reservation.core.publish_failure import PublishFailure
from parking_reservation.repo.sql_loader import load_sql
from parking_reservation.sys.database import DictPool

_PENDING = load_sql("parking_reservation.repo", "select_pending_events")
_MARK_PUBLISHED = load_sql("parking_reservation.repo", "mark_events_published")
_OLDEST = load_sql("parking_reservation.repo", "select_oldest_pending_event")
_COUNT_FAILURE = load_sql("parking_reservation.repo", "count_event_failure")
_MAX_ERROR_LENGTH = 500


class PostgresOutboxRepo:
    def __init__(self, pool: DictPool) -> None:
        self._pool = pool

    def list_pending(self, limit: int, excluded: set[UUID]) -> list[OutboxEvent]:
        with self._pool.connection() as conn:
            rows = conn.execute(_PENDING, {"limit": limit, "excluded": list(excluded)}).fetchall()
        return [OutboxEvent(r["event_id"], r["topic"], r["payload"], r["attempts"]) for r in rows]

    def oldest_pending_created_at(self) -> datetime | None:
        with self._pool.connection() as conn:
            row = conn.execute(_OLDEST).fetchone()
        return None if row is None else row["oldest"]

    def record_batch(
        self, published: list[UUID], failures: list[PublishFailure], park_after: int, now: datetime
    ) -> list[UUID]:
        parked: list[UUID] = []
        with self._pool.connection() as conn, conn.transaction():
            if published:
                conn.execute(_MARK_PUBLISHED, {"event_ids": published, "now": now})
            for failure in failures:
                params = {
                    "event_id": failure.event_id,
                    "error": failure.error[:_MAX_ERROR_LENGTH],
                    "park_after": park_after,
                    "now": now,
                }
                row = conn.execute(_COUNT_FAILURE, params).fetchone()
                if row is not None and row["parked"]:
                    parked.append(failure.event_id)
        return parked
