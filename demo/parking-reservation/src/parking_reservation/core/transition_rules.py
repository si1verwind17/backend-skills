from datetime import datetime

from parking_reservation.core.domain_error import DomainError
from parking_reservation.core.error_code import ErrorCode
from parking_reservation.core.event_topics import (
    CANCELLED_TOPIC,
    CHECKED_IN_TOPIC,
    COMPLETED_TOPIC,
)
from parking_reservation.core.reservation import Reservation
from parking_reservation.core.reservation_status import ReservationStatus
from parking_reservation.core.transition_action import TransitionAction
from parking_reservation.core.transition_decision import TransitionDecision

_SOURCE = {
    TransitionAction.CHECK_IN: ReservationStatus.RESERVED,
    TransitionAction.CHECK_OUT: ReservationStatus.CHECKED_IN,
    TransitionAction.CANCEL: ReservationStatus.RESERVED,
}
_TARGET = {
    TransitionAction.CHECK_IN: ReservationStatus.CHECKED_IN,
    TransitionAction.CHECK_OUT: ReservationStatus.COMPLETED,
    TransitionAction.CANCEL: ReservationStatus.CANCELLED,
}
_TOPIC = {
    TransitionAction.CHECK_IN: CHECKED_IN_TOPIC,
    TransitionAction.CHECK_OUT: COMPLETED_TOPIC,
    TransitionAction.CANCEL: CANCELLED_TOPIC,
}


def source_status(action: TransitionAction) -> ReservationStatus:
    return _SOURCE[action]


def target_status(action: TransitionAction) -> ReservationStatus:
    return _TARGET[action]


def topic_for(action: TransitionAction) -> str:
    return _TOPIC[action]


def decide(action: TransitionAction, reservation: Reservation, now: datetime) -> TransitionDecision:
    """R7, R8, R11, R16 and the lifecycle (requirements UC3-UC5).

    Classified by the reservation's current state only, never by history: a repeat is recognised
    because the state is the one this very call leaves behind.
    """
    status = reservation.status
    if status is _TARGET[action]:
        return TransitionDecision.UNCHANGED
    if status is not _SOURCE[action]:
        raise DomainError(ErrorCode.INVALID_TRANSITION, f"cannot {action.value} a {status.value} reservation")
    if action is TransitionAction.CHECK_IN and now >= reservation.end_at:
        raise DomainError(ErrorCode.CHECKIN_WINDOW_CLOSED, "the reservation window has ended")
    return TransitionDecision.APPLY
