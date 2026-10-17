"""Driver and vehicle rules — pure, no I/O."""

import pytest

from app.domain.drivers import (
    normalize_display_name,
    normalize_email,
    normalize_nickname,
    normalize_phone,
    normalize_plate,
    require_contact,
)
from app.domain.errors import InvalidDriverContact, InvalidPlate


def test_normalize_email_lowercases_domain_only() -> None:
    assert normalize_email(" Jane.Doe@Example.COM ") == "Jane.Doe@example.com"


def test_normalize_email_blank_is_none() -> None:
    assert normalize_email("   ") is None
    assert normalize_email(None) is None


@pytest.mark.parametrize("email", ["jane", "jane@", "@example.com", "jane@example", "a b@example.com"])
def test_normalize_email_rejects_non_addresses(email: str) -> None:
    with pytest.raises(InvalidDriverContact):
        normalize_email(email)


@pytest.mark.parametrize(
    ("raw", "normalized"),
    [("+31 6 1234 5678", "+31612345678"), ("0044 (20) 7946-0958", "+442079460958"), ("+1.415.555.0100", "+14155550100")],
)
def test_normalize_phone_to_e164(raw: str, normalized: str) -> None:
    assert normalize_phone(raw) == normalized


@pytest.mark.parametrize("phone", ["0612345678", "+0123456789", "+12"])
def test_normalize_phone_rejects_non_international_numbers(phone: str) -> None:
    with pytest.raises(InvalidDriverContact):
        normalize_phone(phone)


def test_require_contact_needs_email_or_phone() -> None:
    require_contact("a@example.com", None)
    require_contact(None, "+31612345678")
    with pytest.raises(InvalidDriverContact):
        require_contact(None, None)


def test_normalize_display_name_collapses_whitespace() -> None:
    assert normalize_display_name("  Jane   Doe ") == "Jane Doe"


def test_normalize_display_name_rejects_empty() -> None:
    with pytest.raises(InvalidDriverContact):
        normalize_display_name("   ")


@pytest.mark.parametrize(
    ("plate", "country", "normalized"),
    [
        ("ab12 cde", "GB", "AB12CDE"),
        ("AB-123-CD", "fr", "AB123CD"),
        ("B-MW 1234", "DE", "BMW1234"),
        ("7abc123", "US", "7ABC123"),
        ("12-ABC-3", "NL", "12ABC3"),
        ("ABC 123", "SE", "ABC123"),
    ],
)
def test_normalize_plate(plate: str, country: str, normalized: str) -> None:
    assert normalize_plate(plate, country) == normalized


@pytest.mark.parametrize(("plate", "country"), [("12345678", "FR"), ("ABCDEFGHIJK", "SE"), ("!!", "GB")])
def test_normalize_plate_rejects_bad_shapes(plate: str, country: str) -> None:
    with pytest.raises(InvalidPlate):
        normalize_plate(plate, country)


def test_normalize_plate_rejects_bad_country_codes() -> None:
    with pytest.raises(InvalidPlate):
        normalize_plate("AB12CDE", "GBR")


def test_normalize_nickname_trims_and_limits_length() -> None:
    assert normalize_nickname("  Family   car ") == "Family car"
    assert len(normalize_nickname("x" * 100)) == 40
    assert normalize_nickname(None) == ""
