from enum import Enum


class TransitionAction(Enum):
    """A driver's move on an existing reservation (UC3, UC4, UC5)."""

    CHECK_IN = "check_in"
    CHECK_OUT = "check_out"
    CANCEL = "cancel"
