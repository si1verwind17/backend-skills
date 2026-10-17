"""Tariff administration and price quotes.

A quote prices a prospective stay under the tariff in force on the
stay's first garage-local date and is stored for a short time so the
mobile app can show the same figure on the confirmation screen. The
price computation itself is app/domain/pricing_engine.py.
"""

from __future__ import annotations

from datetime import date, timedelta
from uuid import UUID

from app.domain.errors import (
    GarageNotFound,
    NoTariffInForce,
    QuoteNotFound,
    QuoteWindowTooLong,
    TariffNotFound,
)
from app.domain.models import TimeWindow
from app.domain.ports import Clock, IdGenerator
from app.domain.pricing import NewTariff, PriceBreakdown, Quote, ReservationCharge, Tariff, validate_new_tariff
from app.domain.pricing_engine import first_local_date, price_window
from app.domain.rules import validate_window
from app.repo.charge_repo import ChargeRepo
from app.repo.garage_repo import GarageRepo
from app.repo.quote_repo import QuoteRepo
from app.repo.tariff_repo import TariffRepo


class PricingService:
    def __init__(
        self,
        tariff_repo: TariffRepo,
        quote_repo: QuoteRepo,
        charge_repo: ChargeRepo,
        garage_repo: GarageRepo,
        clock: Clock,
        id_generator: IdGenerator,
        *,
        quote_ttl: timedelta,
        max_quote_days: int,
    ) -> None:
        self._tariffs = tariff_repo
        self._quotes = quote_repo
        self._charges = charge_repo
        self._garages = garage_repo
        self._clock = clock
        self._ids = id_generator
        self._quote_ttl = quote_ttl
        self._max_quote_days = max_quote_days

    # --- tariffs ---------------------------------------------------------

    async def create_tariff(self, tariff: NewTariff) -> Tariff:
        validate_new_tariff(tariff)
        if await self._garages.get(tariff.garage_id) is None:
            raise GarageNotFound(garage_id=tariff.garage_id)
        return await self._tariffs.create(tariff, now=self._clock.now())

    async def get_tariff(self, tariff_id: int) -> Tariff:
        tariff = await self._tariffs.get(tariff_id)
        if tariff is None:
            raise TariffNotFound(tariff_id=tariff_id)
        return tariff

    async def list_tariffs(self, garage_id: int) -> list[Tariff]:
        if await self._garages.get(garage_id) is None:
            raise GarageNotFound(garage_id=garage_id)
        return await self._tariffs.list_by_garage(garage_id)

    async def close_tariff(self, tariff_id: int, *, valid_to: date) -> Tariff:
        """Ends a tariff on valid_to (exclusive) so a successor can take
        over. Closing to a date at or before its start, or later than an
        end it already has, changes nothing and is reported as-is."""
        closed = await self._tariffs.close(tariff_id=tariff_id, valid_to=valid_to)
        if closed is not None:
            return closed
        return await self.get_tariff(tariff_id)

    async def tariff_in_force(self, garage_id: int, on_date: date) -> Tariff:
        tariff = await self._tariffs.find_in_force(garage_id=garage_id, on_date=on_date)
        if tariff is None:
            raise NoTariffInForce(garage_id=garage_id, on_date=on_date.isoformat())
        return tariff

    # --- quotes ----------------------------------------------------------

    async def price(self, *, garage_id: int, window: TimeWindow) -> PriceBreakdown:
        """Prices a window without storing a quote."""
        validate_window(window)
        if window.end - window.start > timedelta(days=self._max_quote_days):
            raise QuoteWindowTooLong(max_days=self._max_quote_days)
        garage = await self._garages.get(garage_id)
        if garage is None:
            raise GarageNotFound(garage_id=garage_id)
        tariff = await self.tariff_in_force(garage_id, first_local_date(window, garage.timezone))
        return price_window(window, tariff, garage.timezone)

    async def create_quote(self, *, garage_id: int, window: TimeWindow) -> Quote:
        breakdown = await self.price(garage_id=garage_id, window=window)
        now = self._clock.now()
        return await self._quotes.create(
            public_id=self._ids.new_quote_public_id(),
            garage_id=garage_id,
            window=window,
            breakdown=breakdown,
            expires_at=now + self._quote_ttl,
            now=now,
        )

    async def get_quote(self, public_id: UUID) -> Quote:
        """Expired quotes are still returned (the app shows "expired, get
        a new price"); callers check Quote.is_expired."""
        quote = await self._quotes.get_by_public_id(public_id)
        if quote is None:
            raise QuoteNotFound(public_id=str(public_id))
        return quote

    def is_expired(self, quote: Quote) -> bool:
        return quote.is_expired(self._clock.now())

    # --- charges ---------------------------------------------------------

    async def get_charge(self, reservation_public_id: UUID) -> ReservationCharge | None:
        return await self._charges.get_for_reservation(reservation_public_id)
