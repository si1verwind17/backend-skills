"""Driver accounts and saved vehicles: domain types and pure rules.

driver_id is the id the mobile app's identity provider already issues;
the account is created on first sign-in with that same id, which is why
reservations made before accounts existed still line up with it.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import datetime

from app.domain.errors import InvalidDriverContact, InvalidPlate

MAX_VEHICLES_PER_DRIVER = 5

_EMAIL = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
_PHONE = re.compile(r"^\+[1-9]\d{6,14}$")

# Per-country plate shapes after normalization (upper case, no spaces or
# dashes). Countries not listed fall back to the generic shape.
_PLATE_SHAPES: dict[str, re.Pattern[str]] = {
    "GB": re.compile(r"^([A-Z]{2}\d{2}[A-Z]{3}|[A-Z]{1,3}\d{1,4}[A-Z]?|[A-Z]\d{1,3}[A-Z]{3})$"),
    "DE": re.compile(r"^[A-Z]{1,3}[A-Z]{1,2}\d{1,4}[EH]?$"),
    "FR": re.compile(r"^[A-Z]{2}\d{3}[A-Z]{2}$"),
    "NL": re.compile(r"^[A-Z0-9]{6}$"),
    "US": re.compile(r"^[A-Z0-9]{2,8}$"),
}
_GENERIC_PLATE = re.compile(r"^[A-Z0-9]{2,10}$")


@dataclass(frozen=True, slots=True)
class Driver:
    driver_id: int
    display_name: str
    email: str | None
    phone: str | None
    notify_reminders: bool
    created_at: datetime
    updated_at: datetime


@dataclass(frozen=True, slots=True)
class DriverPatch:
    display_name: str | None = None
    email: str | None = None
    phone: str | None = None
    notify_reminders: bool | None = None


@dataclass(frozen=True, slots=True)
class Vehicle:
    vehicle_id: int
    driver_id: int
    country_code: str
    plate: str
    nickname: str
    is_default: bool
    created_at: datetime

    @property
    def display_plate(self) -> str:
        return f"{self.plate} ({self.country_code})"


def normalize_email(email: str | None) -> str | None:
    if email is None:
        return None
    cleaned = email.strip()
    if not cleaned:
        return None
    if not _EMAIL.fullmatch(cleaned):
        raise InvalidDriverContact(reason=f"{email!r} is not an email address")
    local, _, domain = cleaned.partition("@")
    return f"{local}@{domain.lower()}"


def normalize_phone(phone: str | None) -> str | None:
    """Phones are stored in E.164 form (+ and digits only). Spaces,
    dashes, dots and brackets typed by the driver are dropped."""
    if phone is None:
        return None
    cleaned = re.sub(r"[\s\-().]", "", phone)
    if not cleaned:
        return None
    if cleaned.startswith("00"):
        cleaned = "+" + cleaned[2:]
    if not _PHONE.fullmatch(cleaned):
        raise InvalidDriverContact(reason=f"{phone!r} is not an international phone number")
    return cleaned


def require_contact(email: str | None, phone: str | None) -> None:
    """Reminders need somewhere to go: an account keeps at least one of
    email or phone at all times."""
    if email is None and phone is None:
        raise InvalidDriverContact(reason="an email address or a phone number is required")


def normalize_display_name(name: str) -> str:
    cleaned = " ".join(name.split())
    if not 1 <= len(cleaned) <= 80:
        raise InvalidDriverContact(reason="display name must be 1-80 characters")
    return cleaned


def normalize_country_code(country_code: str) -> str:
    cleaned = country_code.strip().upper()
    if not re.fullmatch(r"[A-Z]{2}", cleaned):
        raise InvalidPlate(plate="", country_code=country_code)
    return cleaned


def normalize_plate(plate: str, country_code: str) -> str:
    """Upper-cases and strips separators, then checks the plate against
    the country's shape so 'ab12 cde' and 'AB12-CDE' are one vehicle."""
    country = normalize_country_code(country_code)
    cleaned = re.sub(r"[\s\-·.]", "", plate.upper())
    shape = _PLATE_SHAPES.get(country, _GENERIC_PLATE)
    if not shape.fullmatch(cleaned):
        raise InvalidPlate(plate=plate, country_code=country)
    return cleaned


def normalize_nickname(nickname: str | None) -> str:
    if nickname is None:
        return ""
    cleaned = " ".join(nickname.split())
    return cleaned[:40]
