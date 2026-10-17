"""Pure price computation: a time window and a tariff in, a priced
breakdown out. No I/O — the pricing service loads the tariff and the
garage timezone and calls price_window().

How a stay is priced:

1. A stay no longer than the tariff's grace period is free.
2. The stay is cut at local midnights (garage timezone), then each local
   day is cut again at the tariff's band boundaries for that weekday.
3. Each piece is billed per block (block_minutes, 15 by default) at the
   band's rate.
4. Each local day's total is limited to the tariff's daily cap, if any.
5. The sum is rounded to the tariff's rounding increment (half up).
"""

from __future__ import annotations

from datetime import date, datetime, time, timedelta
from zoneinfo import ZoneInfo

from app.domain.garages import MINUTES_PER_DAY
from app.domain.models import TimeWindow
from app.domain.pricing import PriceBreakdown, PriceDay, PriceLine, Tariff, TariffBand

DEFAULT_BLOCK_MINUTES = 15


def minutes_between(start: datetime, end: datetime) -> int:
    """Whole minutes from start to end, counting a started minute as a
    full one (59.5 seconds is one minute). Never negative."""
    seconds = (end - start).total_seconds()
    if seconds <= 0:
        return 0
    return int(-(-seconds // 60))


def billable_blocks(minutes: int, block_minutes: int = DEFAULT_BLOCK_MINUTES) -> int:
    """Number of blocks charged for `minutes` of parking in one band.

    Rounds up to the next started 15-minute block (or the tariff's own
    block length): once a block has begun, the driver pays for all of it.
    """
    if minutes <= 0:
        return 0
    return minutes // block_minutes


def round_to_increment(amount_cents: int, increment_cents: int) -> int:
    """Rounds a non-negative amount to the nearest multiple of
    increment_cents, halves going up (e.g. 1225 -> 1230 at 10)."""
    if increment_cents <= 1:
        return amount_cents
    remainder = amount_cents % increment_cents
    if remainder * 2 >= increment_cents:
        return amount_cents - remainder + increment_cents
    return amount_cents - remainder


def apply_daily_cap(amount_cents: int, daily_cap_cents: int | None) -> int:
    if daily_cap_cents is None:
        return amount_cents
    return min(amount_cents, daily_cap_cents)


def local_instant(local_date: date, minute_of_day: int, tz: ZoneInfo) -> datetime:
    """The instant at `minute_of_day` minutes past local midnight on
    local_date. 1440 means the following midnight."""
    if minute_of_day >= MINUTES_PER_DAY:
        return datetime.combine(local_date + timedelta(days=1), time.min, tzinfo=tz)
    return datetime.combine(local_date, time(minute_of_day // 60, minute_of_day % 60), tzinfo=tz)


def local_dates_touched(window: TimeWindow, tz: ZoneInfo) -> list[date]:
    """Every local calendar date the half-open window [start, end) has at
    least one instant on."""
    first = window.start.astimezone(tz).date()
    last = (window.end - timedelta(microseconds=1)).astimezone(tz).date()
    days = []
    current = first
    while current <= last:
        days.append(current)
        current += timedelta(days=1)
    return days


def _overlap(a_start: datetime, a_end: datetime, b_start: datetime, b_end: datetime) -> tuple[datetime, datetime] | None:
    start = max(a_start, b_start)
    end = min(a_end, b_end)
    if end <= start:
        return None
    return start, end


def _bands_for(tariff: Tariff, weekday: int) -> list[TariffBand]:
    return sorted((b for b in tariff.bands if b.applies_on(weekday)), key=lambda b: b.start_minute)


def price_day(window: TimeWindow, local_date: date, tariff: Tariff, tz: ZoneInfo) -> tuple[PriceDay, list[PriceLine]]:
    """Prices the part of `window` that falls on one local date."""
    lines: list[PriceLine] = []
    for band in _bands_for(tariff, local_date.weekday()):
        band_start = local_instant(local_date, band.start_minute, tz)
        band_end = local_instant(local_date, band.end_minute, tz)
        piece = _overlap(window.start, window.end, band_start, band_end)
        if piece is None:
            continue
        minutes = minutes_between(*piece)
        blocks = billable_blocks(minutes, tariff.block_minutes)
        lines.append(
            PriceLine(
                local_date=local_date,
                start_minute=band.start_minute,
                end_minute=band.end_minute,
                minutes=minutes,
                blocks=blocks,
                rate_cents_per_block=band.rate_cents_per_block,
                amount_cents=blocks * band.rate_cents_per_block,
            )
        )
    uncapped = sum(line.amount_cents for line in lines)
    day = PriceDay(
        local_date=local_date,
        uncapped_cents=uncapped,
        charged_cents=apply_daily_cap(uncapped, tariff.daily_cap_cents),
    )
    return day, lines


def price_window(window: TimeWindow, tariff: Tariff, tz_name: str) -> PriceBreakdown:
    """Prices a whole stay under one tariff. The caller has already
    validated the window (end after start) and picked the tariff in force
    on the stay's first local date."""
    if minutes_between(window.start, window.end) <= tariff.grace_minutes:
        return PriceBreakdown(
            tariff_id=tariff.tariff_id,
            currency=tariff.currency,
            total_cents=0,
            grace_applied=True,
            days=(),
            lines=(),
        )

    tz = ZoneInfo(tz_name)
    days: list[PriceDay] = []
    lines: list[PriceLine] = []
    for local_date in local_dates_touched(window, tz):
        day, day_lines = price_day(window, local_date, tariff, tz)
        days.append(day)
        lines.extend(day_lines)

    total = round_to_increment(sum(d.charged_cents for d in days), tariff.rounding_cents)
    return PriceBreakdown(
        tariff_id=tariff.tariff_id,
        currency=tariff.currency,
        total_cents=total,
        grace_applied=False,
        days=tuple(days),
        lines=tuple(lines),
    )


def charged_window(window: TimeWindow, completed_at: datetime) -> TimeWindow:
    """The period a completed reservation is charged for: the booked
    window, extended to the completion time when the driver overstayed.
    Leaving early does not shorten it."""
    return TimeWindow(start=window.start, end=max(window.end, completed_at))


def first_local_date(window: TimeWindow, tz_name: str) -> date:
    return window.start.astimezone(ZoneInfo(tz_name)).date()
