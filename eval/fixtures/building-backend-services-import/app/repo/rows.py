"""Row -> domain mapping. Kept private to the repo layer (backend-code-
conventions: DB row shapes are fenced off the public interface)."""

from __future__ import annotations

from typing import Any

from app.domain.models import OutboxRow, Reservation, ReservationStatus, TimeWindow


def row_to_reservation(row: dict[str, Any]) -> Reservation:
    return Reservation(
        reservation_id=row["reservation_id"],
        public_id=row["public_id"],
        garage_id=row["garage_id"],
        spot_id=row["spot_id"],
        driver_id=row["driver_id"],
        status=ReservationStatus(row["status"]),
        window=TimeWindow(start=row["window_start"], end=row["window_end"]),
        checked_in_at=row["checked_in_at"],
        completed_at=row["completed_at"],
        cancelled_at=row["cancelled_at"],
        created_at=row["created_at"],
        updated_at=row["updated_at"],
    )


def row_to_outbox_row(row: dict[str, Any]) -> OutboxRow:
    return OutboxRow(
        outbox_id=row["outbox_id"],
        reservation_id=row["reservation_id"],
        reservation_public_id=row["reservation_public_id"],
        driver_id=row["driver_id"],
        garage_id=row["garage_id"],
        spot_id=row["spot_id"],
        window=TimeWindow(start=row["window_start"], end=row["window_end"]),
        completed_at=row["completed_at"],
        attempt_count=row["attempt_count"],
    )
