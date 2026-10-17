from enum import Enum


class TransitionDecision(Enum):
    APPLY = "apply"  # the state changes
    UNCHANGED = "unchanged"  # a repeat of the call that produced the current state
