from datetime import UTC, datetime, timedelta
from uuid import UUID

import pytest

from parking_reservation.core.defect_error import DefectError
from parking_reservation.core.domain_error import DomainError
from parking_reservation.core.error_code import ErrorCode
from parking_reservation.core.reservation_status import ReservationStatus as S
from parking_reservation.core.transition_action import TransitionAction as A
from parking_reservation.services.reservation_service import ReservationService
from testkit.fake_clock import FakeClock
from testkit.sample_reservation import sample_reservation
from testkit.sequential_id_source import SequentialIdSource
from testkit.stub_reservation_repo import StubReservationRepo

NOW = datetime(2026, 10, 20, 11, 0, tzinfo=UTC)
PID = UUID(int=99)


class _TickingClock(FakeClock):
    """Every reading is a later instant, so a second reading shows up as a different timestamp."""

    def __init__(self, start: datetime) -> None:
        super().__init__(start)
        self.reads = 0

    def now(self) -> datetime:
        self.reads += 1
        reading = super().now()
        self.advance(1)
        return reading


def _service(repo: StubReservationRepo) -> ReservationService:
    return ReservationService(repo, FakeClock(NOW), SequentialIdSource())


def test_get_returns_the_drivers_reservation() -> None:
    r = sample_reservation()
    assert _service(StubReservationRepo(finds=[r])).get_reservation(PID, "driver-1") == r


def test_get_of_someone_elses_or_unknown_reservation_is_not_found() -> None:
    with pytest.raises(DomainError) as error:
        _service(StubReservationRepo(finds=[None])).get_reservation(PID, "driver-1")
    assert error.value.code is ErrorCode.RESERVATION_NOT_FOUND


def test_check_in_applies_with_a_fresh_event_id_and_returns_the_re_read_reservation() -> None:
    before = sample_reservation(status=S.RESERVED)
    after = sample_reservation(status=S.CHECKED_IN, checked_in_at=NOW)
    repo = StubReservationRepo(finds=[before, after], applies=[True])
    assert _service(repo).check_in(PID, "driver-1") == after
    assert repo.applied == [(A.CHECK_IN, UUID(int=1), NOW)]


def test_a_repeat_changes_nothing_and_publishes_nothing() -> None:
    done = sample_reservation(status=S.COMPLETED)
    repo = StubReservationRepo(finds=[done], applies=[])
    assert _service(repo).check_out(PID, "driver-1") == done
    assert repo.applied == []


def test_an_illegal_transition_is_rejected_before_the_database_is_asked() -> None:
    repo = StubReservationRepo(finds=[sample_reservation(status=S.CHECKED_IN)], applies=[])
    with pytest.raises(DomainError) as error:
        _service(repo).cancel(PID, "driver-1")
    assert error.value.code is ErrorCode.INVALID_TRANSITION
    assert repo.applied == []


def test_losing_a_race_re_reads_and_re_decides() -> None:
    reserved = sample_reservation(status=S.RESERVED)
    cancelled = sample_reservation(status=S.CANCELLED, cancelled_at=NOW)
    repo = StubReservationRepo(finds=[reserved, cancelled], applies=[False])
    with pytest.raises(DomainError) as error:
        _service(repo).check_in(PID, "driver-1")
    assert error.value.code is ErrorCode.INVALID_TRANSITION


def test_losing_a_race_to_the_same_call_is_a_repeat() -> None:
    reserved = sample_reservation(status=S.RESERVED)
    checked_in = sample_reservation(status=S.CHECKED_IN, checked_in_at=NOW)
    repo = StubReservationRepo(finds=[reserved, checked_in], applies=[False])
    assert _service(repo).check_in(PID, "driver-1") == checked_in


def test_a_guard_that_disagrees_with_the_rules_is_a_defect() -> None:
    reserved = sample_reservation(status=S.RESERVED)
    repo = StubReservationRepo(finds=[reserved], applies=[False])
    with pytest.raises(DefectError):
        _service(repo).cancel(PID, "driver-1")
    assert len(repo.applied) == 1


def test_the_decision_and_the_recorded_instant_are_the_same_reading_of_the_clock() -> None:
    repo = StubReservationRepo(finds=[sample_reservation(status=S.RESERVED)], applies=[True])
    clock = _TickingClock(NOW)
    service = ReservationService(repo, clock, SequentialIdSource())
    service.check_in(PID, "driver-1")
    assert repo.applied[0][2] == NOW
    assert clock.reads == 1


def test_check_in_after_the_window_is_closed() -> None:
    late = FakeClock(NOW + timedelta(hours=3))
    repo = StubReservationRepo(finds=[sample_reservation(status=S.RESERVED)], applies=[])
    with pytest.raises(DomainError) as error:
        ReservationService(repo, late, SequentialIdSource()).check_in(PID, "driver-1")
    assert error.value.code is ErrorCode.CHECKIN_WINDOW_CLOSED
