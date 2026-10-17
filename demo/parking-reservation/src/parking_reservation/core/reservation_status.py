from enum import Enum


class ReservationStatus(Enum):
    """Lifecycle states (requirements UC3-UC5); values equal the database enum labels."""

    RESERVED = "reserved"
    CHECKED_IN = "checked_in"
    COMPLETED = "completed"
    CANCELLED = "cancelled"
