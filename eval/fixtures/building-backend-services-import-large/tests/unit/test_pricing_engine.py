"""Pure pricing-engine tests — data in, data out, no mocks."""

from datetime import UTC, date, datetime, timedelta

import pytest

from app.domain.models import TimeWindow
from app.domain.pricing import ALL_WEEKDAYS_MASK, Tariff, TariffBand
from app.domain.pricing_engine import (
    apply_daily_cap,
    billable_blocks,
    charged_window,
    first_local_date,
    local_dates_touched,
    minutes_between,
    price_window,
    round_to_increment,
)

# 2026-08-17 is a Monday.
MONDAY = datetime(2026, 8, 17, tzinfo=UTC)
WEEKDAYS = 0b0011111
WEEKEND = 0b1100000


def _tariff(
    *,
    bands: tuple[TariffBand, ...] | None = None,
    block_minutes: int = 15,
    grace_minutes: int = 0,
    daily_cap_cents: int | None = None,
    rounding_cents: int = 1,
) -> Tariff:
    return Tariff(
        tariff_id=1,
        garage_id=1,
        name="Standard",
        currency="EUR",
        block_minutes=block_minutes,
        grace_minutes=grace_minutes,
        daily_cap_cents=daily_cap_cents,
        rounding_cents=rounding_cents,
        valid_from=date(2026, 1, 1),
        valid_to=None,
        bands=bands or (TariffBand(1, ALL_WEEKDAYS_MASK, 0, 1440, 100),),
    )


def _day_night_tariff(**kwargs) -> Tariff:
    """Day rate 08:00-20:00 (150/block), night rate otherwise (50/block)."""
    return _tariff(
        bands=(
            TariffBand(1, ALL_WEEKDAYS_MASK, 0, 480, 50),
            TariffBand(2, ALL_WEEKDAYS_MASK, 480, 1200, 150),
            TariffBand(3, ALL_WEEKDAYS_MASK, 1200, 1440, 50),
        ),
        **kwargs,
    )


def _window(start: datetime, minutes: int) -> TimeWindow:
    return TimeWindow(start=start, end=start + timedelta(minutes=minutes))


# --- minutes_between -------------------------------------------------------


def test_minutes_between_counts_whole_minutes() -> None:
    assert minutes_between(MONDAY, MONDAY + timedelta(minutes=90)) == 90


def test_minutes_between_counts_a_started_minute_as_full() -> None:
    assert minutes_between(MONDAY, MONDAY + timedelta(minutes=10, seconds=1)) == 11


def test_minutes_between_is_never_negative() -> None:
    assert minutes_between(MONDAY, MONDAY - timedelta(minutes=5)) == 0


# --- billable_blocks -------------------------------------------------------


def test_billable_blocks_exact_multiple() -> None:
    assert billable_blocks(60) == 4


def test_billable_blocks_zero_minutes_is_zero_blocks() -> None:
    assert billable_blocks(0) == 0


def test_billable_blocks_partial_block_is_charged_as_a_full_block() -> None:
    """A started block is a full block: 1 minute is one block."""
    assert billable_blocks(1) == 1


def test_billable_blocks_rounds_up_to_the_next_started_block() -> None:
    assert billable_blocks(16) == 2
    assert billable_blocks(61) == 5


def test_billable_blocks_respects_the_tariff_block_length() -> None:
    assert billable_blocks(31, block_minutes=30) == 2
    assert billable_blocks(60, block_minutes=30) == 2


# --- money rounding and caps ----------------------------------------------


@pytest.mark.parametrize(
    ("amount", "increment", "expected"),
    [
        (1234, 1, 1234),
        (1224, 10, 1220),
        (1225, 10, 1230),
        (1226, 10, 1230),
        (1202, 5, 1200),
        (1203, 5, 1205),
        (1249, 50, 1250),
        (1224, 50, 1200),
        (0, 100, 0),
    ],
)
def test_round_to_increment_rounds_half_up(amount: int, increment: int, expected: int) -> None:
    assert round_to_increment(amount, increment) == expected


def test_apply_daily_cap_limits_the_amount() -> None:
    assert apply_daily_cap(5000, 2000) == 2000


def test_apply_daily_cap_without_cap_is_identity() -> None:
    assert apply_daily_cap(5000, None) == 5000


# --- local dates -----------------------------------------------------------


def test_local_dates_touched_single_day() -> None:
    window = _window(MONDAY + timedelta(hours=9), 120)
    assert local_dates_touched(window, _zone("UTC")) == [date(2026, 8, 17)]


def test_local_dates_touched_ending_at_midnight_excludes_next_day() -> None:
    window = TimeWindow(start=MONDAY + timedelta(hours=22), end=MONDAY + timedelta(days=1))
    assert local_dates_touched(window, _zone("UTC")) == [date(2026, 8, 17)]


def test_local_dates_touched_uses_garage_timezone() -> None:
    # 23:00 UTC Monday is 01:00 Tuesday in Berlin (CEST, UTC+2).
    window = _window(MONDAY + timedelta(hours=23), 60)
    assert local_dates_touched(window, _zone("Europe/Berlin")) == [date(2026, 8, 18)]


def test_first_local_date_uses_garage_timezone() -> None:
    window = _window(MONDAY + timedelta(hours=23), 60)
    assert first_local_date(window, "America/New_York") == date(2026, 8, 17)
    assert first_local_date(window, "Asia/Tokyo") == date(2026, 8, 18)


# --- price_window ----------------------------------------------------------


def test_price_window_flat_rate_whole_hours() -> None:
    breakdown = price_window(_window(MONDAY + timedelta(hours=9), 120), _tariff(), "UTC")

    assert breakdown.total_cents == 8 * 100
    assert breakdown.currency == "EUR"
    assert not breakdown.grace_applied
    assert [line.blocks for line in breakdown.lines] == [8]


def test_price_window_charges_a_started_block_in_full() -> None:
    """70 minutes is five 15-minute blocks (the fifth block was started)."""
    breakdown = price_window(_window(MONDAY + timedelta(hours=9), 70), _tariff(), "UTC")

    assert breakdown.lines[0].minutes == 70
    assert breakdown.lines[0].blocks == 5
    assert breakdown.total_cents == 500


def test_price_window_within_grace_is_free() -> None:
    breakdown = price_window(_window(MONDAY + timedelta(hours=9), 10), _tariff(grace_minutes=10), "UTC")

    assert breakdown.total_cents == 0
    assert breakdown.grace_applied
    assert breakdown.lines == ()


def test_price_window_just_past_grace_is_charged_from_the_start() -> None:
    breakdown = price_window(_window(MONDAY + timedelta(hours=9), 30), _tariff(grace_minutes=10), "UTC")

    assert not breakdown.grace_applied
    assert breakdown.total_cents == 200


def test_price_window_splits_at_band_boundaries() -> None:
    # 19:00-21:00: one hour of day rate, one hour of night rate.
    breakdown = price_window(_window(MONDAY + timedelta(hours=19), 120), _day_night_tariff(), "UTC")

    assert [(line.start_minute, line.blocks, line.amount_cents) for line in breakdown.lines] == [
        (480, 4, 600),
        (1200, 4, 200),
    ]
    assert breakdown.total_cents == 800


def test_price_window_band_boundaries_follow_garage_local_time() -> None:
    # 06:00-08:00 UTC is 08:00-10:00 in Berlin: all day rate.
    breakdown = price_window(_window(MONDAY + timedelta(hours=6), 120), _day_night_tariff(), "Europe/Berlin")

    assert [line.start_minute for line in breakdown.lines] == [480]
    assert breakdown.total_cents == 8 * 150


def test_price_window_weekday_and_weekend_bands() -> None:
    tariff = _tariff(
        bands=(
            TariffBand(1, WEEKDAYS, 0, 1440, 100),
            TariffBand(2, WEEKEND, 0, 1440, 60),
        )
    )
    saturday = MONDAY + timedelta(days=5, hours=10)

    breakdown = price_window(_window(saturday, 60), tariff, "UTC")

    assert breakdown.total_cents == 4 * 60


def test_price_window_applies_daily_cap_per_local_day() -> None:
    # Monday 12:00 to Tuesday 12:00 at 100/block: 48 blocks per 12 hours,
    # 4800 uncapped on each day, capped to 3000 each.
    window = _window(MONDAY + timedelta(hours=12), 24 * 60)

    breakdown = price_window(window, _tariff(daily_cap_cents=3000), "UTC")

    assert [d.local_date for d in breakdown.days] == [date(2026, 8, 17), date(2026, 8, 18)]
    assert [d.uncapped_cents for d in breakdown.days] == [4800, 4800]
    assert [d.charged_cents for d in breakdown.days] == [3000, 3000]
    assert all(d.capped for d in breakdown.days)
    assert breakdown.total_cents == 6000


def test_price_window_rounds_total_to_increment() -> None:
    tariff = _tariff(bands=(TariffBand(1, ALL_WEEKDAYS_MASK, 0, 1440, 33),), rounding_cents=10)

    breakdown = price_window(_window(MONDAY + timedelta(hours=9), 60), tariff, "UTC")

    assert breakdown.total_cents == 130  # 4 x 33 = 132 -> 130


def test_price_window_across_dst_change_uses_local_bands() -> None:
    # Europe/Berlin leaves summer time on 2026-10-25 at 03:00 local.
    # 2026-10-25 00:00 UTC (02:00 CEST) to 04:00 UTC (05:00 CET): four
    # real hours, all in the night band.
    start = datetime(2026, 10, 25, 0, tzinfo=UTC)

    breakdown = price_window(_window(start, 240), _day_night_tariff(), "Europe/Berlin")

    assert sum(line.minutes for line in breakdown.lines) == 240
    assert breakdown.total_cents == 16 * 50


# --- charged_window --------------------------------------------------------


def test_charged_window_extends_on_overstay() -> None:
    booked = _window(MONDAY, 60)
    completed_at = MONDAY + timedelta(minutes=95)

    assert charged_window(booked, completed_at) == TimeWindow(start=MONDAY, end=completed_at)


def test_charged_window_does_not_shrink_when_leaving_early() -> None:
    booked = _window(MONDAY, 60)

    assert charged_window(booked, MONDAY + timedelta(minutes=20)) == booked


def _zone(name: str):
    from zoneinfo import ZoneInfo

    return ZoneInfo(name)
