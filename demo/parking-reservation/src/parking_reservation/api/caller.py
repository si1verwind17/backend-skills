from dataclasses import dataclass


@dataclass(frozen=True)
class Caller:
    """The authenticated caller, as vouched for by the gateway (AD6)."""

    subject: str
    is_staff: bool
