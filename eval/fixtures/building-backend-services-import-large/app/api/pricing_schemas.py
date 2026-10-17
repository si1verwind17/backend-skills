"""Wire contract for tariffs, quotes and charges. Amounts are integer
minor units (cents) with an ISO-4217 currency, never floats."""

from __future__ import annotations

from datetime import date, datetime
from typing import Annotated
from uuid import UUID

from pydantic import BaseModel, Field

from app.domain.errors import InvalidOpeningHours, InvalidTariff
from app.domain.garages import WEEKDAY_NAMES, format_clock, parse_clock
from app.domain.pricing import (
    NewTariff,
    NewTariffBand,
    PriceBreakdown,
    Quote,
    ReservationCharge,
    Tariff,
    TariffBand,
    weekday_mask,
    weekdays_from_mask,
)

_WEEKDAY = "^(mon|tue|wed|thu|fri|sat|sun)$"


class TariffBandModel(BaseModel):
    weekdays: list[Annotated[str, Field(pattern=_WEEKDAY)]] = Field(min_length=1, max_length=7)
    starts: str
    ends: str
    rate_cents_per_block: int = Field(ge=0)

    def to_domain(self) -> NewTariffBand:
        try:
            start_minute = parse_clock(self.starts)
            end_minute = parse_clock(self.ends)
        except InvalidOpeningHours as exc:
            raise InvalidTariff(reason=exc.reason) from exc
        return NewTariffBand(
            weekday_mask=weekday_mask([WEEKDAY_NAMES.index(d) for d in self.weekdays]),
            start_minute=start_minute,
            end_minute=end_minute,
            rate_cents_per_block=self.rate_cents_per_block,
        )

    @classmethod
    def from_domain(cls, band: TariffBand) -> TariffBandModel:
        return cls(
            weekdays=[WEEKDAY_NAMES[d] for d in weekdays_from_mask(band.weekday_mask)],
            starts=format_clock(band.start_minute),
            ends=format_clock(band.end_minute),
            rate_cents_per_block=band.rate_cents_per_block,
        )


class TariffCreateRequest(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    currency: str = Field(min_length=3, max_length=3)
    block_minutes: int = Field(default=15, gt=0)
    grace_minutes: int = Field(default=0, ge=0)
    daily_cap_cents: int | None = Field(default=None, gt=0)
    rounding_cents: int = 1
    valid_from: date
    valid_to: date | None = None
    bands: list[TariffBandModel] = Field(min_length=1, max_length=50)

    def to_domain(self, garage_id: int) -> NewTariff:
        return NewTariff(
            garage_id=garage_id,
            name=self.name.strip(),
            currency=self.currency.upper(),
            block_minutes=self.block_minutes,
            grace_minutes=self.grace_minutes,
            daily_cap_cents=self.daily_cap_cents,
            rounding_cents=self.rounding_cents,
            valid_from=self.valid_from,
            valid_to=self.valid_to,
            bands=tuple(b.to_domain() for b in self.bands),
        )


class TariffCloseRequest(BaseModel):
    valid_to: date


class TariffResponse(BaseModel):
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
    bands: list[TariffBandModel]

    @classmethod
    def from_domain(cls, tariff: Tariff) -> TariffResponse:
        return cls(
            tariff_id=tariff.tariff_id,
            garage_id=tariff.garage_id,
            name=tariff.name,
            currency=tariff.currency,
            block_minutes=tariff.block_minutes,
            grace_minutes=tariff.grace_minutes,
            daily_cap_cents=tariff.daily_cap_cents,
            rounding_cents=tariff.rounding_cents,
            valid_from=tariff.valid_from,
            valid_to=tariff.valid_to,
            bands=[TariffBandModel.from_domain(b) for b in tariff.bands],
        )


class QuoteRequest(BaseModel):
    window_start: datetime
    window_end: datetime


class PriceLineModel(BaseModel):
    local_date: date
    band_starts: str
    band_ends: str
    minutes: int
    blocks: int
    rate_cents_per_block: int
    amount_cents: int


class PriceDayModel(BaseModel):
    local_date: date
    uncapped_cents: int
    charged_cents: int
    capped: bool


class PriceBreakdownModel(BaseModel):
    currency: str
    total_cents: int
    grace_applied: bool
    days: list[PriceDayModel]
    lines: list[PriceLineModel]

    @classmethod
    def from_domain(cls, breakdown: PriceBreakdown) -> PriceBreakdownModel:
        return cls(
            currency=breakdown.currency,
            total_cents=breakdown.total_cents,
            grace_applied=breakdown.grace_applied,
            days=[
                PriceDayModel(
                    local_date=d.local_date,
                    uncapped_cents=d.uncapped_cents,
                    charged_cents=d.charged_cents,
                    capped=d.capped,
                )
                for d in breakdown.days
            ],
            lines=[
                PriceLineModel(
                    local_date=line.local_date,
                    band_starts=format_clock(line.start_minute),
                    band_ends=format_clock(line.end_minute),
                    minutes=line.minutes,
                    blocks=line.blocks,
                    rate_cents_per_block=line.rate_cents_per_block,
                    amount_cents=line.amount_cents,
                )
                for line in breakdown.lines
            ],
        )


class QuoteResponse(BaseModel):
    quote_id: UUID
    garage_id: int
    tariff_id: int
    window_start: datetime
    window_end: datetime
    amount_cents: int
    currency: str
    expires_at: datetime
    expired: bool
    breakdown: PriceBreakdownModel

    @classmethod
    def from_domain(cls, quote: Quote, *, expired: bool) -> QuoteResponse:
        return cls(
            quote_id=quote.public_id,
            garage_id=quote.garage_id,
            tariff_id=quote.tariff_id,
            window_start=quote.window.start,
            window_end=quote.window.end,
            amount_cents=quote.amount_cents,
            currency=quote.currency,
            expires_at=quote.expires_at,
            expired=expired,
            breakdown=PriceBreakdownModel.from_domain(quote.breakdown),
        )


class ChargeResponse(BaseModel):
    reservation_id: UUID
    tariff_id: int
    charged_from: datetime
    charged_until: datetime
    amount_cents: int
    currency: str
    settled_at: datetime

    @classmethod
    def from_domain(cls, reservation_public_id: UUID, charge: ReservationCharge) -> ChargeResponse:
        return cls(
            reservation_id=reservation_public_id,
            tariff_id=charge.tariff_id,
            charged_from=charge.charged_window.start,
            charged_until=charge.charged_window.end,
            amount_cents=charge.amount_cents,
            currency=charge.currency,
            settled_at=charge.settled_at,
        )


class SettlementRunResponse(BaseModel):
    claimed: int
    settled: int
    unpriced: int
    already_settled: int
