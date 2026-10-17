from enum import Enum


class CreateOutcome(Enum):
    """Outcomes of the database create call; values equal the labels reserve_spot returns."""

    CREATED = "created"
    REPLAYED = "replayed"
    KEY_REUSED = "key_reused"
    NO_SPOT = "no_spot"
    GARAGE_NOT_FOUND = "garage_not_found"
