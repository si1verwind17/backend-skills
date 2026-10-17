"""Domain types for tariffs, quotes and settled charges, plus the pure
validation rules a tariff must pass before it is stored.

Money is always an integer number of minor units (cents) alongside an
ISO-4217 currency code; no floats anywhere in pricing.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import date, datetime
from uuid import UUID

from app.domain.errors import InvalidTariff
from app.domain.garages import MINUTES_PER_DAY, WEEKDAY_NAMES
from app.domain.models import TimeWindow

ALLOWED_ROUNDING_CENTS = (1, 5, 10, 50, 100)
MAX_BLOCK_MINUTES = 240
ALL_WEEKDAYS_MASK = 0b1111111

_CURRENCY = re.compile(r"^[A-Z]{3}$")


@dataclass(frozen=True, slots=True)
class TariffBand:
    """Rate applying on the weekdays in weekday_mask (bit 0 = Monday) to
    local time [start_minute, end_minute)."""

    band_id: int
    weekday_mask: int
    start_minute: int
    end_minute: int
    rate_cents_per_block: int

    def applies_on(self, weekday: int) -> bool:
        return bool(self.weekday_mask & (1 << weekday))


@dataclass(frozen=True, slots=True)
class Tariff:
    tariff_id: int
    garage_id: int
    name: str
    currency: str
    block_minutes: int
    grace_minutes: int
    daily_cap_cents: int | None
    rounding_cents: int
    valid_from: date
    valid_to: date | None
    bands: tuple[TariffBand, ...] = field(default=())

    def in_force_on(self, on_date: date) -> bool:
        return self.valid_from <= on_date and (self.valid_to is None or on_date < self.valid_to)


@dataclass(frozen=True, slots=True)
class NewTariffBand:
    weekday_mask: int
    start_minute: int
    end_minute: int
    rate_cents_per_block: int


@dataclass(frozen=True, slots=True)
class NewTariff:
    garage_id: int
    name: str
    currency: str
    block_minutes: int
    grace_minutes: int
    daily_cap_cents: int | None
    rounding_cents: int
    valid_from: date
    valid_to: date | None
    bands: tuple[NewTariffBand, ...]


@dataclass(frozen=True, slots=True)
class PriceLine:
    """One band's contribution on one local day."""

    local_date: date
    start_minute: int
    end_minute: int
    minutes: int
    blocks: int
    rate_cents_per_block: int
    amount_cents: int


@dataclass(frozen=True, slots=True)
class PriceDay:
    local_date: date
    uncapped_cents: int
    charged_cents: int

    @property
    def capped(self) -> bool:
        return self.charged_cents < self.uncapped_cents


@dataclass(frozen=True, slots=True)
class PriceBreakdown:
    tariff_id: int
    currency: str
    total_cents: int
    grace_applied: bool
    days: tuple[PriceDay, ...]
    lines: tuple[PriceLine, ...]


@dataclass(frozen=True, slots=True)
class Quote:
    quote_id: int
    public_id: UUID
    garage_id: int
    tariff_id: int
    window: TimeWindow
    amount_cents: int
    currency: str
    breakdown: PriceBreakdown
    expires_at: datetime
    created_at: datetime

    def is_expired(self, now: datetime) -> bool:
        return now >= self.expires_at


@dataclass(frozen=True, slots=True)
class UnsettledReservation:
    """A completed reservation that has no charge yet, with everything the
    settlement step needs to price it."""

    reservation_id: int
    garage_id: int
    timezone: str
    window: TimeWindow
    completed_at: datetime


@dataclass(frozen=True, slots=True)
class ReservationCharge:
    charge_id: int
    reservation_id: int
    garage_id: int
    tariff_id: int
    charged_window: TimeWindow
    amount_cents: int
    currency: str
    settled_at: datetime


def weekday_mask(weekdays: list[int]) -> int:
    mask = 0
    for weekday in weekdays:
        if not 0 <= weekday <= 6:
            raise InvalidTariff(reason=f"weekday {weekday} is outside 0-6")
        mask |= 1 << weekday
    return mask


def weekdays_from_mask(mask: int) -> list[int]:
    return [d for d in range(7) if mask & (1 << d)]


def validate_new_tariff(tariff: NewTariff) -> None:
    """Shape and coverage checks for a tariff before it is stored.

    Every weekday must be covered from 00:00 to 24:00 by exactly one band
    at every minute, so the pricing engine never meets an unpriced minute
    and never has to choose between two rates.
    """
    if not _CURRENCY.fullmatch(tariff.currency):
        raise InvalidTariff(reason=f"currency {tariff.currency!r} is not an ISO-4217 code")
    if not 0 < tariff.block_minutes <= MAX_BLOCK_MINUTES:
        raise InvalidTariff(reason=f"block_minutes must be between 1 and {MAX_BLOCK_MINUTES}")
    if MINUTES_PER_DAY % tariff.block_minutes != 0:
        raise InvalidTariff(reason="block_minutes must divide a day evenly")
    if tariff.grace_minutes < 0:
        raise InvalidTariff(reason="grace_minutes cannot be negative")
    if tariff.rounding_cents not in ALLOWED_ROUNDING_CENTS:
        raise InvalidTariff(reason=f"rounding_cents must be one of {ALLOWED_ROUNDING_CENTS}")
    if tariff.daily_cap_cents is not None and tariff.daily_cap_cents <= 0:
        raise InvalidTariff(reason="daily_cap_cents must be positive when set")
    if tariff.valid_to is not None and tariff.valid_to <= tariff.valid_from:
        raise InvalidTariff(reason="valid_to must be after valid_from")
    if not tariff.bands:
        raise InvalidTariff(reason="a tariff needs at least one band")
    for band in tariff.bands:
        _validate_band(band)
    for weekday in range(7):
        _validate_day_coverage(weekday, [b for b in tariff.bands if b.weekday_mask & (1 << weekday)])


def _validate_band(band: NewTariffBand) -> None:
    if not 1 <= band.weekday_mask <= ALL_WEEKDAYS_MASK:
        raise InvalidTariff(reason="a band must apply to at least one weekday")
    if band.start_minute < 0 or band.end_minute > MINUTES_PER_DAY:
        raise InvalidTariff(reason="a band must stay within 00:00-24:00")
    if band.end_minute <= band.start_minute:
        raise InvalidTariff(reason="a band must end after it starts")
    if band.rate_cents_per_block < 0:
        raise InvalidTariff(reason="a band's rate cannot be negative")


def _validate_day_coverage(weekday: int, bands: list[NewTariffBand]) -> None:
    name = WEEKDAY_NAMES[weekday]
    cursor = 0
    for band in sorted(bands, key=lambda b: b.start_minute):
        if band.start_minute > cursor:
            raise InvalidTariff(reason=f"{name} has no band covering minute {cursor}")
        if band.start_minute < cursor:
            raise InvalidTariff(reason=f"{name} has overlapping bands at minute {band.start_minute}")
        cursor = band.end_minute
    if cursor != MINUTES_PER_DAY:
        raise InvalidTariff(reason=f"{name} has no band covering minute {cursor}")
