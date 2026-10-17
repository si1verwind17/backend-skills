"""Tariff validation rules — pure, no I/O."""

from datetime import date

import pytest

from app.domain.errors import InvalidTariff
from app.domain.pricing import (
    ALL_WEEKDAYS_MASK,
    NewTariff,
    NewTariffBand,
    validate_new_tariff,
    weekday_mask,
    weekdays_from_mask,
)


def _tariff(**overrides) -> NewTariff:
    fields = {
        "garage_id": 1,
        "name": "Standard",
        "currency": "EUR",
        "block_minutes": 15,
        "grace_minutes": 10,
        "daily_cap_cents": 2500,
        "rounding_cents": 5,
        "valid_from": date(2026, 9, 1),
        "valid_to": None,
        "bands": (NewTariffBand(ALL_WEEKDAYS_MASK, 0, 1440, 120),),
    }
    fields.update(overrides)
    return NewTariff(**fields)


def test_a_full_coverage_tariff_is_valid() -> None:
    validate_new_tariff(_tariff())  # must not raise


def test_split_day_bands_covering_every_minute_are_valid() -> None:
    validate_new_tariff(
        _tariff(
            bands=(
                NewTariffBand(ALL_WEEKDAYS_MASK, 0, 480, 50),
                NewTariffBand(ALL_WEEKDAYS_MASK, 480, 1200, 150),
                NewTariffBand(ALL_WEEKDAYS_MASK, 1200, 1440, 50),
            )
        )
    )


def test_weekday_and_weekend_bands_are_valid() -> None:
    validate_new_tariff(
        _tariff(
            bands=(
                NewTariffBand(weekday_mask([0, 1, 2, 3, 4]), 0, 1440, 120),
                NewTariffBand(weekday_mask([5, 6]), 0, 1440, 80),
            )
        )
    )


def test_a_gap_in_coverage_is_rejected() -> None:
    with pytest.raises(InvalidTariff, match="no band covering minute 480"):
        validate_new_tariff(
            _tariff(
                bands=(
                    NewTariffBand(ALL_WEEKDAYS_MASK, 0, 480, 50),
                    NewTariffBand(ALL_WEEKDAYS_MASK, 600, 1440, 150),
                )
            )
        )


def test_overlapping_bands_are_rejected() -> None:
    with pytest.raises(InvalidTariff, match="overlapping"):
        validate_new_tariff(
            _tariff(
                bands=(
                    NewTariffBand(ALL_WEEKDAYS_MASK, 0, 600, 50),
                    NewTariffBand(ALL_WEEKDAYS_MASK, 480, 1440, 150),
                )
            )
        )


def test_a_weekday_without_bands_is_rejected() -> None:
    with pytest.raises(InvalidTariff, match="sun"):
        validate_new_tariff(_tariff(bands=(NewTariffBand(weekday_mask([0, 1, 2, 3, 4, 5]), 0, 1440, 100),)))


def test_bands_must_end_at_midnight() -> None:
    with pytest.raises(InvalidTariff, match="minute 1380"):
        validate_new_tariff(_tariff(bands=(NewTariffBand(ALL_WEEKDAYS_MASK, 0, 1380, 100),)))


@pytest.mark.parametrize("currency", ["eur", "EURO", "E1R", ""])
def test_currency_must_be_iso_code(currency: str) -> None:
    with pytest.raises(InvalidTariff, match="currency"):
        validate_new_tariff(_tariff(currency=currency))


@pytest.mark.parametrize("block_minutes", [0, -15, 241])
def test_block_minutes_must_be_in_range(block_minutes: int) -> None:
    with pytest.raises(InvalidTariff, match="block_minutes"):
        validate_new_tariff(_tariff(block_minutes=block_minutes))


def test_block_minutes_must_divide_a_day() -> None:
    with pytest.raises(InvalidTariff, match="divide"):
        validate_new_tariff(_tariff(block_minutes=7))


def test_rounding_must_be_an_allowed_increment() -> None:
    with pytest.raises(InvalidTariff, match="rounding_cents"):
        validate_new_tariff(_tariff(rounding_cents=3))


def test_daily_cap_must_be_positive() -> None:
    with pytest.raises(InvalidTariff, match="daily_cap_cents"):
        validate_new_tariff(_tariff(daily_cap_cents=0))


def test_negative_grace_is_rejected() -> None:
    with pytest.raises(InvalidTariff, match="grace"):
        validate_new_tariff(_tariff(grace_minutes=-1))


def test_validity_must_end_after_it_starts() -> None:
    with pytest.raises(InvalidTariff, match="valid_to"):
        validate_new_tariff(_tariff(valid_to=date(2026, 9, 1)))


def test_negative_rate_is_rejected() -> None:
    with pytest.raises(InvalidTariff, match="rate"):
        validate_new_tariff(_tariff(bands=(NewTariffBand(ALL_WEEKDAYS_MASK, 0, 1440, -1),)))


def test_empty_band_list_is_rejected() -> None:
    with pytest.raises(InvalidTariff, match="at least one band"):
        validate_new_tariff(_tariff(bands=()))


def test_weekday_mask_round_trips() -> None:
    mask = weekday_mask([0, 2, 6])

    assert mask == 0b1000101
    assert weekdays_from_mask(mask) == [0, 2, 6]


def test_weekday_mask_rejects_out_of_range_days() -> None:
    with pytest.raises(InvalidTariff):
        weekday_mask([7])
