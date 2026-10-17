"""In-memory fakes standing in for the repo layer, used by stubbed
orchestration tests (tests/unit/test_reservation_service.py,
test_outbox_publisher_service.py) — backend-code-conventions tier 2:
"service logic with repos/clients stubbed. Verifies wiring, not the
database." Real SQL/constraint behavior is only trusted from the
integration tier (tests/integration/).
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from datetime import date, datetime
from uuid import UUID

from app.domain.drivers import Driver, Vehicle
from app.domain.errors import (
    DriverAlreadyExists,
    DuplicateOperator,
    DuplicateSpotCode,
    DuplicateVehicle,
    OperatorNotFound,
    OverlappingTariff,
    UnknownSpotType,
)
from app.domain.garages import (
    DailyHours,
    GarageDetails,
    GaragePatch,
    NewSpot,
    Operator,
    Spot,
    SpotPatch,
    SpotType,
    WeeklyHours,
)
from app.domain.models import (
    Garage,
    OutboxRow,
    Reservation,
    ReservationStatus,
    TimeWindow,
)
from app.domain.notifications import NotificationRow, SkipReason
from app.domain.pricing import (
    NewTariff,
    PriceBreakdown,
    Quote,
    ReservationCharge,
    Tariff,
    TariffBand,
    UnsettledReservation,
)
from app.domain.reports import DateRange, OccupancyRow, RevenueRow, StatusCount


class FakeReservationRepo:
    def __init__(self) -> None:
        self.by_public_id: dict[UUID, Reservation] = {}
        self._next_id = 1

    def seed(self, reservation: Reservation) -> None:
        self.by_public_id[reservation.public_id] = reservation

    async def create_reservation(
        self, *, public_id: UUID, garage_id: int, driver_id: int, window: TimeWindow
    ) -> Reservation:
        reservation = Reservation(
            reservation_id=self._next_id,
            public_id=public_id,
            garage_id=garage_id,
            spot_id=1,
            driver_id=driver_id,
            status=ReservationStatus.RESERVED,
            window=window,
            checked_in_at=None,
            completed_at=None,
            cancelled_at=None,
            created_at=window.start,
            updated_at=window.start,
        )
        self._next_id += 1
        self.by_public_id[public_id] = reservation
        return reservation

    async def _transition(
        self, public_id: UUID, now: datetime, from_status: ReservationStatus, to_status: ReservationStatus, ts_field: str
    ) -> Reservation | None:
        reservation = self.by_public_id.get(public_id)
        if reservation is None or reservation.status != from_status:
            return None
        updated = replace(reservation, status=to_status, updated_at=now, **{ts_field: now})
        self.by_public_id[public_id] = updated
        return updated

    async def check_in(self, *, public_id: UUID, now: datetime) -> Reservation | None:
        return await self._transition(
            public_id, now, ReservationStatus.RESERVED, ReservationStatus.CHECKED_IN, "checked_in_at"
        )

    async def complete(self, *, public_id: UUID, now: datetime) -> Reservation | None:
        return await self._transition(
            public_id, now, ReservationStatus.CHECKED_IN, ReservationStatus.COMPLETED, "completed_at"
        )

    async def cancel(self, *, public_id: UUID, now: datetime) -> Reservation | None:
        return await self._transition(
            public_id, now, ReservationStatus.RESERVED, ReservationStatus.CANCELLED, "cancelled_at"
        )

    async def get_by_public_id(self, public_id: UUID) -> Reservation | None:
        return self.by_public_id.get(public_id)

    async def list_by_driver(self, driver_id: int) -> list[Reservation]:
        return [r for r in self.by_public_id.values() if r.driver_id == driver_id]

    async def list_by_garage_and_window(
        self, *, garage_id: int, range_start: datetime, range_end: datetime
    ) -> list[Reservation]:
        return [
            r
            for r in self.by_public_id.values()
            if r.garage_id == garage_id and r.window.start < range_end and r.window.end > range_start
        ]


class FakeGarageRepo:
    def __init__(self) -> None:
        self.by_id: dict[int, Garage] = {}

    def seed(self, garage: Garage) -> None:
        self.by_id[garage.garage_id] = garage

    async def get(self, garage_id: int) -> Garage | None:
        return self.by_id.get(garage_id)


class FakeOutboxClaim:
    def __init__(self, rows: list[OutboxRow]) -> None:
        self.rows = rows
        self.published_ids: list[int] = []
        self.failed: list[tuple[int, str]] = []

    async def mark_published(self, outbox_id: int, now: datetime) -> None:
        self.published_ids.append(outbox_id)

    async def mark_failed(self, outbox_id: int, now: datetime, error: str) -> None:
        self.failed.append((outbox_id, error))


class FakeOutboxRepo:
    def __init__(self, rows: list[OutboxRow]) -> None:
        self._rows = rows
        self.last_claim: FakeOutboxClaim | None = None

    def claim_batch(self, limit: int):
        claim = FakeOutboxClaim(self._rows[:limit])
        self.last_claim = claim
        return _ClaimContext(claim)


class _ClaimContext:
    def __init__(self, claim: FakeOutboxClaim) -> None:
        self._claim = claim

    async def __aenter__(self) -> FakeOutboxClaim:
        return self._claim

    async def __aexit__(self, *exc_info: object) -> None:
        return None


# --- garage and spot administration ------------------------------------------


DEFAULT_SPOT_TYPES = [
    SpotType(spot_type_id=1, code="standard", description="Standard car space"),
    SpotType(spot_type_id=2, code="compact", description="Compact car space"),
    SpotType(spot_type_id=3, code="ev", description="Space with an electric vehicle charger"),
]


class FakeOperatorRepo:
    def __init__(self) -> None:
        self.by_id: dict[int, Operator] = {}
        self._next_id = 1

    async def create(self, *, name: str, contact_email: str, now: datetime) -> Operator:
        if any(o.name == name for o in self.by_id.values()):
            raise DuplicateOperator(name=name)
        operator = Operator(
            operator_id=self._next_id, name=name, contact_email=contact_email, created_at=now, updated_at=now
        )
        self.by_id[operator.operator_id] = operator
        self._next_id += 1
        return operator

    async def get(self, operator_id: int) -> Operator | None:
        return self.by_id.get(operator_id)

    async def list(self, *, limit: int, offset: int) -> list[Operator]:
        ordered = sorted(self.by_id.values(), key=lambda o: o.name)
        return ordered[offset : offset + limit]

    async def update(
        self, *, operator_id: int, name: str | None, contact_email: str | None, now: datetime
    ) -> Operator | None:
        current = self.by_id.get(operator_id)
        if current is None:
            return None
        updated = replace(
            current,
            name=name if name is not None else current.name,
            contact_email=contact_email if contact_email is not None else current.contact_email,
            updated_at=now,
        )
        self.by_id[operator_id] = updated
        return updated


class FakeGarageAdminRepo:
    def __init__(self, operators: FakeOperatorRepo | None = None) -> None:
        self._operators = operators
        self.by_id: dict[int, GarageDetails] = {}
        self.hours: dict[int, tuple[DailyHours, ...]] = {}
        self._next_id = 1

    def seed(self, garage: GarageDetails) -> None:
        self.by_id[garage.garage_id] = garage
        self._next_id = max(self._next_id, garage.garage_id + 1)

    async def create(
        self, *, operator_id: int, name: str, address: str, timezone: str, now: datetime
    ) -> GarageDetails:
        if self._operators is not None and operator_id not in self._operators.by_id:
            raise OperatorNotFound(operator_id=operator_id)
        garage = GarageDetails(
            garage_id=self._next_id,
            operator_id=operator_id,
            name=name,
            address=address,
            timezone=timezone,
            is_active=True,
            created_at=now,
            updated_at=now,
        )
        self.by_id[garage.garage_id] = garage
        self._next_id += 1
        return garage

    async def get(self, garage_id: int) -> GarageDetails | None:
        return self.by_id.get(garage_id)

    async def list_by_operator(self, operator_id: int, *, include_inactive: bool) -> list[GarageDetails]:
        return [
            g
            for g in sorted(self.by_id.values(), key=lambda g: (g.name, g.garage_id))
            if g.operator_id == operator_id and (include_inactive or g.is_active)
        ]

    async def update(self, *, garage_id: int, patch: GaragePatch, now: datetime) -> GarageDetails | None:
        current = self.by_id.get(garage_id)
        if current is None:
            return None
        updated = replace(
            current,
            name=patch.name if patch.name is not None else current.name,
            address=patch.address if patch.address is not None else current.address,
            timezone=patch.timezone if patch.timezone is not None else current.timezone,
            is_active=patch.is_active if patch.is_active is not None else current.is_active,
            updated_at=now,
        )
        self.by_id[garage_id] = updated
        return updated

    async def get_opening_hours(self, garage_id: int) -> WeeklyHours:
        return WeeklyHours(garage_id=garage_id, days=self.hours.get(garage_id, ()))

    async def replace_opening_hours(self, garage_id: int, days: tuple[DailyHours, ...]) -> WeeklyHours:
        self.hours[garage_id] = days
        return WeeklyHours(garage_id=garage_id, days=days)


class FakeSpotRepo:
    def __init__(self, spot_types: list[SpotType] | None = None) -> None:
        self.spot_types = list(spot_types if spot_types is not None else DEFAULT_SPOT_TYPES)
        self.by_id: dict[int, Spot] = {}
        self.open_reservations: dict[int, int] = {}
        self._next_id = 1

    async def list_spot_types(self) -> list[SpotType]:
        return list(self.spot_types)

    async def create_many(self, *, garage_id: int, spots: list[NewSpot], now: datetime) -> list[Spot]:
        known = {t.code for t in self.spot_types}
        existing = {s.code for s in self.by_id.values() if s.garage_id == garage_id}
        for spot in spots:
            if spot.spot_type not in known:
                raise UnknownSpotType(code=spot.spot_type)
            if spot.code in existing:
                raise DuplicateSpotCode(garage_id=garage_id, code=spot.code)
        created = []
        for spot in spots:
            row = Spot(
                spot_id=self._next_id,
                garage_id=garage_id,
                code=spot.code,
                spot_type=spot.spot_type,
                level=spot.level,
                is_active=True,
                created_at=now,
                updated_at=now,
            )
            self.by_id[row.spot_id] = row
            self._next_id += 1
            created.append(row)
        return created

    async def get(self, spot_id: int) -> Spot | None:
        return self.by_id.get(spot_id)

    async def list_by_garage(self, garage_id: int, *, spot_type: str | None, include_inactive: bool) -> list[Spot]:
        return [
            s
            for s in sorted(self.by_id.values(), key=lambda s: (s.level, s.code))
            if s.garage_id == garage_id
            and (spot_type is None or s.spot_type == spot_type)
            and (include_inactive or s.is_active)
        ]

    async def update(self, *, spot_id: int, patch: SpotPatch, now: datetime) -> Spot | None:
        current = self.by_id.get(spot_id)
        if current is None:
            return None
        updated = replace(
            current,
            spot_type=patch.spot_type if patch.spot_type is not None else current.spot_type,
            level=patch.level if patch.level is not None else current.level,
            is_active=patch.is_active if patch.is_active is not None else current.is_active,
            updated_at=now,
        )
        self.by_id[spot_id] = updated
        return updated

    async def count_open_reservations(self, *, spot_id: int, now: datetime) -> int:
        return self.open_reservations.get(spot_id, 0)

    async def count_active(self, garage_id: int) -> int:
        return sum(1 for s in self.by_id.values() if s.garage_id == garage_id and s.is_active)


# --- pricing -----------------------------------------------------------------


class FakeTariffRepo:
    def __init__(self) -> None:
        self.by_id: dict[int, Tariff] = {}
        self.find_calls: list[tuple[int, date]] = []
        self._next_id = 1

    def seed(self, tariff: Tariff) -> None:
        self.by_id[tariff.tariff_id] = tariff
        self._next_id = max(self._next_id, tariff.tariff_id + 1)

    async def create(self, tariff: NewTariff, *, now: datetime) -> Tariff:
        for existing in self.by_id.values():
            if existing.garage_id != tariff.garage_id:
                continue
            new_end = tariff.valid_to or date.max
            old_end = existing.valid_to or date.max
            if tariff.valid_from < old_end and existing.valid_from < new_end:
                raise OverlappingTariff(garage_id=tariff.garage_id)
        tariff_id = self._next_id
        self._next_id += 1
        stored = Tariff(
            tariff_id=tariff_id,
            garage_id=tariff.garage_id,
            name=tariff.name,
            currency=tariff.currency,
            block_minutes=tariff.block_minutes,
            grace_minutes=tariff.grace_minutes,
            daily_cap_cents=tariff.daily_cap_cents,
            rounding_cents=tariff.rounding_cents,
            valid_from=tariff.valid_from,
            valid_to=tariff.valid_to,
            bands=tuple(
                TariffBand(
                    band_id=n + 1,
                    weekday_mask=b.weekday_mask,
                    start_minute=b.start_minute,
                    end_minute=b.end_minute,
                    rate_cents_per_block=b.rate_cents_per_block,
                )
                for n, b in enumerate(tariff.bands)
            ),
        )
        self.by_id[tariff_id] = stored
        return stored

    async def get(self, tariff_id: int) -> Tariff | None:
        return self.by_id.get(tariff_id)

    async def find_in_force(self, *, garage_id: int, on_date: date) -> Tariff | None:
        self.find_calls.append((garage_id, on_date))
        for tariff in self.by_id.values():
            if tariff.garage_id == garage_id and tariff.in_force_on(on_date):
                return tariff
        return None

    async def list_by_garage(self, garage_id: int) -> list[Tariff]:
        return sorted(
            (replace(t, bands=()) for t in self.by_id.values() if t.garage_id == garage_id),
            key=lambda t: t.valid_from,
            reverse=True,
        )

    async def close(self, *, tariff_id: int, valid_to: date) -> Tariff | None:
        tariff = self.by_id.get(tariff_id)
        if tariff is None or tariff.valid_from >= valid_to:
            return None
        if tariff.valid_to is not None and tariff.valid_to <= valid_to:
            return None
        closed = replace(tariff, valid_to=valid_to)
        self.by_id[tariff_id] = closed
        return replace(closed, bands=())


class FakeQuoteRepo:
    def __init__(self) -> None:
        self.by_public_id: dict[UUID, Quote] = {}
        self._next_id = 1

    async def create(
        self,
        *,
        public_id: UUID,
        garage_id: int,
        window: TimeWindow,
        breakdown: PriceBreakdown,
        expires_at: datetime,
        now: datetime,
    ) -> Quote:
        quote = Quote(
            quote_id=self._next_id,
            public_id=public_id,
            garage_id=garage_id,
            tariff_id=breakdown.tariff_id,
            window=window,
            amount_cents=breakdown.total_cents,
            currency=breakdown.currency,
            breakdown=breakdown,
            expires_at=expires_at,
            created_at=now,
        )
        self._next_id += 1
        self.by_public_id[public_id] = quote
        return quote

    async def get_by_public_id(self, public_id: UUID) -> Quote | None:
        return self.by_public_id.get(public_id)


@dataclass
class RecordedCharge:
    reservation_id: int
    tariff_id: int
    charged_window: TimeWindow
    amount_cents: int
    currency: str


class FakeSettlementClaim:
    def __init__(self, rows: list[UnsettledReservation], already_charged: set[int]) -> None:
        self.rows = rows
        self._already_charged = already_charged
        self.recorded: list[RecordedCharge] = []

    async def record_charge(
        self,
        *,
        reservation: UnsettledReservation,
        tariff_id: int,
        charged_window: TimeWindow,
        amount_cents: int,
        currency: str,
        now: datetime,
    ) -> bool:
        if reservation.reservation_id in self._already_charged:
            return False
        self._already_charged.add(reservation.reservation_id)
        self.recorded.append(
            RecordedCharge(
                reservation_id=reservation.reservation_id,
                tariff_id=tariff_id,
                charged_window=charged_window,
                amount_cents=amount_cents,
                currency=currency,
            )
        )
        return True


class FakeChargeRepo:
    def __init__(self, rows: list[UnsettledReservation] | None = None) -> None:
        self._rows = rows or []
        self.already_charged: set[int] = set()
        self.charges_by_public_id: dict[UUID, ReservationCharge] = {}
        self.last_claim: FakeSettlementClaim | None = None

    def claim_unsettled(self, limit: int):
        claim = FakeSettlementClaim(self._rows[:limit], self.already_charged)
        self.last_claim = claim
        return _ClaimContext(claim)

    async def get_for_reservation(self, public_id: UUID) -> ReservationCharge | None:
        return self.charges_by_public_id.get(public_id)


# --- drivers and vehicles ----------------------------------------------------


class FakeDriverRepo:
    def __init__(self) -> None:
        self.by_id: dict[int, Driver] = {}

    def seed(self, driver: Driver) -> None:
        self.by_id[driver.driver_id] = driver

    async def create(
        self,
        *,
        driver_id: int,
        display_name: str,
        email: str | None,
        phone: str | None,
        notify_reminders: bool,
        now: datetime,
    ) -> Driver:
        if driver_id in self.by_id:
            raise DriverAlreadyExists(driver_id=driver_id)
        driver = Driver(
            driver_id=driver_id,
            display_name=display_name,
            email=email,
            phone=phone,
            notify_reminders=notify_reminders,
            created_at=now,
            updated_at=now,
        )
        self.by_id[driver_id] = driver
        return driver

    async def get(self, driver_id: int) -> Driver | None:
        return self.by_id.get(driver_id)

    async def save(self, driver: Driver, *, now: datetime) -> Driver | None:
        if driver.driver_id not in self.by_id:
            return None
        saved = replace(driver, updated_at=now)
        self.by_id[driver.driver_id] = saved
        return saved


class FakeVehicleRepo:
    def __init__(self) -> None:
        self.by_id: dict[int, Vehicle] = {}
        self._next_id = 1

    def _active(self, driver_id: int) -> list[Vehicle]:
        return sorted(
            (v for v in self.by_id.values() if v.driver_id == driver_id),
            key=lambda v: (v.created_at, v.vehicle_id),
        )

    async def list_for_driver(self, driver_id: int) -> list[Vehicle]:
        return sorted(self._active(driver_id), key=lambda v: not v.is_default)

    async def count_for_driver(self, driver_id: int) -> int:
        return len(self._active(driver_id))

    async def add(self, *, driver_id: int, country_code: str, plate: str, nickname: str, now: datetime) -> Vehicle:
        current = self._active(driver_id)
        if any(v.country_code == country_code and v.plate == plate for v in current):
            raise DuplicateVehicle(plate=plate)
        vehicle = Vehicle(
            vehicle_id=self._next_id,
            driver_id=driver_id,
            country_code=country_code,
            plate=plate,
            nickname=nickname,
            is_default=not current,
            created_at=now,
        )
        self.by_id[vehicle.vehicle_id] = vehicle
        self._next_id += 1
        return vehicle

    async def get(self, *, driver_id: int, vehicle_id: int) -> Vehicle | None:
        vehicle = self.by_id.get(vehicle_id)
        return vehicle if vehicle is not None and vehicle.driver_id == driver_id else None

    async def remove(self, *, driver_id: int, vehicle_id: int, now: datetime) -> bool:
        vehicle = await self.get(driver_id=driver_id, vehicle_id=vehicle_id)
        if vehicle is None:
            return False
        del self.by_id[vehicle_id]
        remaining = self._active(driver_id)
        if vehicle.is_default and remaining:
            oldest = remaining[0]
            self.by_id[oldest.vehicle_id] = replace(oldest, is_default=True)
        return True

    async def make_default(self, *, driver_id: int, vehicle_id: int) -> Vehicle | None:
        if await self.get(driver_id=driver_id, vehicle_id=vehicle_id) is None:
            return None
        for v in self._active(driver_id):
            self.by_id[v.vehicle_id] = replace(v, is_default=v.vehicle_id == vehicle_id)
        return self.by_id[vehicle_id]


# --- reports -----------------------------------------------------------------


class FakeReportRepo:
    def __init__(self) -> None:
        self.occupancy_rows: list[OccupancyRow] = []
        self.revenue_rows: list[RevenueRow] = []
        self.status_counts: list[StatusCount] = []
        self.last_timezone: str | None = None
        self.last_range: DateRange | None = None

    async def occupancy_by_day(self, *, garage_id: int, timezone: str, date_range: DateRange) -> list[OccupancyRow]:
        self.last_timezone = timezone
        self.last_range = date_range
        return list(self.occupancy_rows)

    async def revenue_by_garage_day(self, *, operator_id: int, date_range: DateRange) -> list[RevenueRow]:
        self.last_range = date_range
        return list(self.revenue_rows)

    async def status_breakdown(self, *, garage_id: int, date_range: DateRange) -> list[StatusCount]:
        self.last_range = date_range
        return list(self.status_counts)


# --- notifications -----------------------------------------------------------


class FakeNotificationClaim:
    def __init__(self, rows: list[NotificationRow]) -> None:
        self.rows = rows
        self.published_ids: list[int] = []
        self.failed: list[tuple[int, str]] = []
        self.skipped: list[tuple[int, SkipReason]] = []

    async def mark_published(self, notification_id: int, now: datetime) -> None:
        self.published_ids.append(notification_id)

    async def mark_failed(self, notification_id: int, now: datetime, error: str) -> None:
        self.failed.append((notification_id, error))

    async def mark_skipped(self, notification_id: int, now: datetime, reason: SkipReason) -> None:
        self.skipped.append((notification_id, reason))


class FakeNotificationRepo:
    def __init__(self, due_rows: list[NotificationRow] | None = None, scheduled: int = 0) -> None:
        self._due_rows = due_rows or []
        self._scheduled = scheduled
        self.schedule_calls: list[tuple[TimeWindow, object, datetime]] = []
        self.claim_args: dict | None = None
        self.last_claim: FakeNotificationClaim | None = None

    async def schedule_reminders(self, *, scheduling_range: TimeWindow, lead, now: datetime) -> int:
        self.schedule_calls.append((scheduling_range, lead, now))
        return self._scheduled

    def claim_due(self, *, now: datetime, limit: int, max_attempts: int):
        self.claim_args = {"now": now, "limit": limit, "max_attempts": max_attempts}
        claim = FakeNotificationClaim(self._due_rows[:limit])
        self.last_claim = claim
        return _ClaimContext(claim)
