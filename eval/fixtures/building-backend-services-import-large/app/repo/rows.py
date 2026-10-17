"""Row -> domain mapping. Kept private to the repo layer (backend-code-
conventions: DB row shapes are fenced off the public interface)."""

from __future__ import annotations

from typing import Any

from app.domain.drivers import Driver, Vehicle
from app.domain.garages import DailyHours, GarageDetails, Operator, Spot, SpotType
from app.domain.models import OutboxRow, Reservation, ReservationStatus, TimeWindow
from app.domain.notifications import NotificationKind, NotificationRow
from app.domain.pricing import ReservationCharge, Tariff, TariffBand, UnsettledReservation


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


def row_to_operator(row: dict[str, Any]) -> Operator:
    return Operator(
        operator_id=row["operator_id"],
        name=row["name"],
        contact_email=row["contact_email"],
        created_at=row["created_at"],
        updated_at=row["updated_at"],
    )


def row_to_garage_details(row: dict[str, Any]) -> GarageDetails:
    return GarageDetails(
        garage_id=row["garage_id"],
        operator_id=row["operator_id"],
        name=row["name"],
        address=row["address"],
        timezone=row["timezone"],
        is_active=row["is_active"],
        created_at=row["created_at"],
        updated_at=row["updated_at"],
    )


def row_to_daily_hours(row: dict[str, Any]) -> DailyHours:
    return DailyHours(
        weekday=row["weekday"],
        open_minute=row["open_minute"],
        close_minute=row["close_minute"],
    )


def row_to_spot_type(row: dict[str, Any]) -> SpotType:
    return SpotType(spot_type_id=row["spot_type_id"], code=row["code"], description=row["description"])


def row_to_spot(row: dict[str, Any]) -> Spot:
    return Spot(
        spot_id=row["spot_id"],
        garage_id=row["garage_id"],
        code=row["code"],
        spot_type=row["spot_type"],
        level=row["level"],
        is_active=row["is_active"],
        created_at=row["created_at"],
        updated_at=row["updated_at"],
    )


def row_to_tariff_band(row: dict[str, Any]) -> TariffBand:
    return TariffBand(
        band_id=row["band_id"],
        weekday_mask=row["weekday_mask"],
        start_minute=row["start_minute"],
        end_minute=row["end_minute"],
        rate_cents_per_block=row["rate_cents_per_block"],
    )


def row_to_tariff(row: dict[str, Any], bands: list[TariffBand]) -> Tariff:
    return Tariff(
        tariff_id=row["tariff_id"],
        garage_id=row["garage_id"],
        name=row["name"],
        currency=row["currency"].strip(),
        block_minutes=row["block_minutes"],
        grace_minutes=row["grace_minutes"],
        daily_cap_cents=row["daily_cap_cents"],
        rounding_cents=row["rounding_cents"],
        valid_from=row["valid_from"],
        valid_to=row["valid_to"],
        bands=tuple(bands),
    )


def row_to_unsettled_reservation(row: dict[str, Any]) -> UnsettledReservation:
    return UnsettledReservation(
        reservation_id=row["reservation_id"],
        garage_id=row["garage_id"],
        timezone=row["timezone"],
        window=TimeWindow(start=row["window_start"], end=row["window_end"]),
        completed_at=row["completed_at"],
    )


def row_to_reservation_charge(row: dict[str, Any]) -> ReservationCharge:
    return ReservationCharge(
        charge_id=row["charge_id"],
        reservation_id=row["reservation_id"],
        garage_id=row["garage_id"],
        tariff_id=row["tariff_id"],
        charged_window=TimeWindow(start=row["charged_from"], end=row["charged_until"]),
        amount_cents=row["amount_cents"],
        currency=row["currency"].strip(),
        settled_at=row["settled_at"],
    )


def row_to_driver(row: dict[str, Any]) -> Driver:
    return Driver(
        driver_id=row["driver_id"],
        display_name=row["display_name"],
        email=row["email"],
        phone=row["phone"],
        notify_reminders=row["notify_reminders"],
        created_at=row["created_at"],
        updated_at=row["updated_at"],
    )


def row_to_vehicle(row: dict[str, Any]) -> Vehicle:
    return Vehicle(
        vehicle_id=row["vehicle_id"],
        driver_id=row["driver_id"],
        country_code=row["country_code"].strip(),
        plate=row["plate"],
        nickname=row["nickname"],
        is_default=row["is_default"],
        created_at=row["created_at"],
    )


def row_to_notification_row(row: dict[str, Any]) -> NotificationRow:
    return NotificationRow(
        notification_id=row["notification_id"],
        kind=NotificationKind(row["kind"]),
        reservation_id=row["reservation_id"],
        reservation_public_id=row["reservation_public_id"],
        reservation_status=ReservationStatus(row["reservation_status"]),
        driver_id=row["driver_id"],
        garage_id=row["garage_id"],
        garage_name=row["garage_name"],
        window=TimeWindow(start=row["window_start"], end=row["window_end"]),
        send_after=row["send_after"],
        attempt_count=row["attempt_count"],
        driver_email=row["email"],
        driver_phone=row["phone"],
        notify_reminders=row["notify_reminders"],
    )
