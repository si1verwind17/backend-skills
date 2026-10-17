"""Stubbed orchestration tests for GarageAdminService — repos are fakes
(tests/unit/fakes.py). Uniqueness and foreign-key behavior is only trusted
from the integration tier; these check validation order and error
translation."""

from datetime import UTC, datetime

import pytest

from app.domain.errors import (
    DuplicateOperator,
    DuplicateSpotCode,
    GarageNotFound,
    InvalidOpeningHours,
    InvalidSpotCode,
    InvalidTimezone,
    OperatorNotFound,
    SpotHasActiveReservations,
    SpotNotFound,
    UnknownSpotType,
)
from app.domain.garages import DailyHours, GaragePatch, NewSpot, SpotPatch
from app.domain.ports import FixedClock
from app.services.garage_admin_service import GarageAdminService
from tests.unit.fakes import FakeGarageAdminRepo, FakeOperatorRepo, FakeSpotRepo

NOW = datetime(2026, 8, 15, 12, tzinfo=UTC)


def _service() -> tuple[GarageAdminService, FakeOperatorRepo, FakeGarageAdminRepo, FakeSpotRepo]:
    operators = FakeOperatorRepo()
    garages = FakeGarageAdminRepo(operators)
    spots = FakeSpotRepo()
    service = GarageAdminService(operators, garages, spots, FixedClock(NOW))
    return service, operators, garages, spots


async def _garage(service: GarageAdminService, timezone: str = "Europe/London") -> int:
    operator = await service.create_operator(name="CityPark", contact_email="ops@citypark.example")
    garage = await service.create_garage(
        operator_id=operator.operator_id, name="Riverside", address="1 Quay St", timezone=timezone
    )
    return garage.garage_id


# --- operators ---------------------------------------------------------------


@pytest.mark.asyncio
async def test_create_operator_trims_name_and_email() -> None:
    service, _, _, _ = _service()

    operator = await service.create_operator(name="  CityPark ", contact_email=" ops@citypark.example ")

    assert operator.name == "CityPark"
    assert operator.contact_email == "ops@citypark.example"
    assert operator.created_at == NOW


@pytest.mark.asyncio
async def test_duplicate_operator_name_is_a_conflict() -> None:
    service, _, _, _ = _service()
    await service.create_operator(name="CityPark", contact_email="a@x.example")

    with pytest.raises(DuplicateOperator):
        await service.create_operator(name="CityPark", contact_email="b@x.example")


@pytest.mark.asyncio
async def test_get_unknown_operator_raises_not_found() -> None:
    service, _, _, _ = _service()

    with pytest.raises(OperatorNotFound):
        await service.get_operator(404)


@pytest.mark.asyncio
async def test_update_operator_changes_only_given_fields() -> None:
    service, _, _, _ = _service()
    operator = await service.create_operator(name="CityPark", contact_email="a@x.example")

    updated = await service.update_operator(operator.operator_id, name=None, contact_email=" new@x.example ")

    assert updated.name == "CityPark"
    assert updated.contact_email == "new@x.example"


@pytest.mark.asyncio
async def test_update_unknown_operator_raises_not_found() -> None:
    service, _, _, _ = _service()

    with pytest.raises(OperatorNotFound):
        await service.update_operator(404, name="X", contact_email=None)


@pytest.mark.asyncio
async def test_list_operators_pages_by_name() -> None:
    service, _, _, _ = _service()
    for name in ("Charlie", "Alpha", "Bravo"):
        await service.create_operator(name=name, contact_email=f"{name.lower()}@x.example")

    page = await service.list_operators(limit=2, offset=1)

    assert [o.name for o in page] == ["Bravo", "Charlie"]


# --- garages -----------------------------------------------------------------


@pytest.mark.asyncio
async def test_create_garage_rejects_unknown_timezone_before_writing() -> None:
    service, operators, garages, _ = _service()
    operator = await service.create_operator(name="CityPark", contact_email="a@x.example")

    with pytest.raises(InvalidTimezone):
        await service.create_garage(
            operator_id=operator.operator_id, name="Riverside", address="", timezone="Mars/Olympus"
        )

    assert garages.by_id == {}


@pytest.mark.asyncio
async def test_create_garage_for_unknown_operator_raises_not_found() -> None:
    service, _, _, _ = _service()

    with pytest.raises(OperatorNotFound):
        await service.create_garage(operator_id=99, name="Riverside", address="", timezone="UTC")


@pytest.mark.asyncio
async def test_get_unknown_garage_raises_not_found() -> None:
    service, _, _, _ = _service()

    with pytest.raises(GarageNotFound):
        await service.get_garage(404)


@pytest.mark.asyncio
async def test_list_garages_hides_inactive_unless_asked() -> None:
    service, _, _, _ = _service()
    operator = await service.create_operator(name="CityPark", contact_email="a@x.example")
    open_garage = await service.create_garage(
        operator_id=operator.operator_id, name="A", address="", timezone="UTC"
    )
    closed = await service.create_garage(operator_id=operator.operator_id, name="B", address="", timezone="UTC")
    await service.update_garage(closed.garage_id, GaragePatch(is_active=False))

    active_only = await service.list_garages(operator.operator_id, include_inactive=False)
    everything = await service.list_garages(operator.operator_id, include_inactive=True)

    assert [g.garage_id for g in active_only] == [open_garage.garage_id]
    assert {g.garage_id for g in everything} == {open_garage.garage_id, closed.garage_id}


@pytest.mark.asyncio
async def test_list_garages_of_unknown_operator_raises_not_found() -> None:
    service, _, _, _ = _service()

    with pytest.raises(OperatorNotFound):
        await service.list_garages(404, include_inactive=False)


@pytest.mark.asyncio
async def test_update_garage_validates_a_new_timezone() -> None:
    service, _, _, _ = _service()
    garage_id = await _garage(service)

    with pytest.raises(InvalidTimezone):
        await service.update_garage(garage_id, GaragePatch(timezone="Not/AZone"))


@pytest.mark.asyncio
async def test_update_garage_keeps_unpatched_fields() -> None:
    service, _, _, _ = _service()
    garage_id = await _garage(service)

    updated = await service.update_garage(garage_id, GaragePatch(name="Riverside North"))

    assert updated.name == "Riverside North"
    assert updated.timezone == "Europe/London"
    assert updated.address == "1 Quay St"


@pytest.mark.asyncio
async def test_update_unknown_garage_raises_not_found() -> None:
    service, _, _, _ = _service()

    with pytest.raises(GarageNotFound):
        await service.update_garage(404, GaragePatch(name="X"))


# --- opening hours -----------------------------------------------------------


@pytest.mark.asyncio
async def test_set_opening_hours_stores_days_sorted_by_weekday() -> None:
    service, _, _, _ = _service()
    garage_id = await _garage(service)

    hours = await service.set_opening_hours(
        garage_id,
        [
            DailyHours(weekday=5, open_minute=8 * 60, close_minute=20 * 60),
            DailyHours(weekday=0, open_minute=0, close_minute=24 * 60),
        ],
    )

    assert [d.weekday for d in hours.days] == [0, 5]
    stored = await service.get_opening_hours(garage_id)
    assert stored.for_weekday(0).is_all_day
    assert stored.for_weekday(3) is None


@pytest.mark.asyncio
async def test_set_opening_hours_rejects_a_repeated_weekday() -> None:
    service, _, _, _ = _service()
    garage_id = await _garage(service)

    with pytest.raises(InvalidOpeningHours):
        await service.set_opening_hours(
            garage_id,
            [
                DailyHours(weekday=1, open_minute=0, close_minute=600),
                DailyHours(weekday=1, open_minute=700, close_minute=900),
            ],
        )


@pytest.mark.asyncio
async def test_set_opening_hours_validates_before_looking_up_the_garage() -> None:
    """Invalid input is a 422 even for a garage that doesn't exist."""
    service, _, _, _ = _service()

    with pytest.raises(InvalidOpeningHours):
        await service.set_opening_hours(404, [DailyHours(weekday=2, open_minute=600, close_minute=600)])


@pytest.mark.asyncio
async def test_set_opening_hours_for_unknown_garage_raises_not_found() -> None:
    service, _, _, _ = _service()

    with pytest.raises(GarageNotFound):
        await service.set_opening_hours(404, [DailyHours(weekday=2, open_minute=600, close_minute=900)])


@pytest.mark.asyncio
async def test_get_opening_hours_for_unknown_garage_raises_not_found() -> None:
    service, _, _, _ = _service()

    with pytest.raises(GarageNotFound):
        await service.get_opening_hours(404)


# --- spots -------------------------------------------------------------------


@pytest.mark.asyncio
async def test_add_spots_normalizes_codes_and_trims_level() -> None:
    service, _, _, _ = _service()
    garage_id = await _garage(service)

    spots = await service.add_spots(
        garage_id,
        [
            NewSpot(code="a 12", spot_type="standard", level=" L1 "),
            NewSpot(code="ev1", spot_type="ev", level="L1"),
        ],
    )

    assert [s.code for s in spots] == ["A-12", "EV1"]
    assert spots[0].level == "L1"
    assert spots[1].spot_type == "ev"


@pytest.mark.asyncio
async def test_add_spots_rejects_codes_repeated_within_the_request() -> None:
    service, _, _, spot_repo = _service()
    garage_id = await _garage(service)

    with pytest.raises(DuplicateSpotCode):
        await service.add_spots(
            garage_id,
            [NewSpot(code="A1", spot_type="standard", level=""), NewSpot(code="a1", spot_type="standard", level="")],
        )

    assert spot_repo.by_id == {}


@pytest.mark.asyncio
async def test_add_spots_rejects_a_code_already_in_the_garage() -> None:
    service, _, _, _ = _service()
    garage_id = await _garage(service)
    await service.add_spots(garage_id, [NewSpot(code="A1", spot_type="standard", level="")])

    with pytest.raises(DuplicateSpotCode):
        await service.add_spots(garage_id, [NewSpot(code="A1", spot_type="standard", level="")])


@pytest.mark.asyncio
async def test_add_spots_rejects_an_unknown_spot_type() -> None:
    service, _, _, _ = _service()
    garage_id = await _garage(service)

    with pytest.raises(UnknownSpotType):
        await service.add_spots(garage_id, [NewSpot(code="A1", spot_type="helipad", level="")])


@pytest.mark.asyncio
async def test_add_spots_rejects_an_unpaintable_code() -> None:
    service, _, _, _ = _service()
    garage_id = await _garage(service)

    with pytest.raises(InvalidSpotCode):
        await service.add_spots(garage_id, [NewSpot(code="A/1", spot_type="standard", level="")])


@pytest.mark.asyncio
async def test_add_spots_to_unknown_garage_raises_not_found() -> None:
    service, _, _, _ = _service()

    with pytest.raises(GarageNotFound):
        await service.add_spots(404, [NewSpot(code="A1", spot_type="standard", level="")])


@pytest.mark.asyncio
async def test_add_spot_range_expands_and_pads_codes() -> None:
    service, _, _, _ = _service()
    garage_id = await _garage(service)

    spots = await service.add_spot_range(
        garage_id, prefix="B", first=8, last=11, width=2, spot_type="compact", level="L2"
    )

    assert [s.code for s in spots] == ["B08", "B09", "B10", "B11"]
    assert {s.spot_type for s in spots} == {"compact"}


@pytest.mark.asyncio
async def test_add_spot_range_with_last_before_first_creates_nothing() -> None:
    service, _, _, _ = _service()
    garage_id = await _garage(service)

    spots = await service.add_spot_range(
        garage_id, prefix="B", first=5, last=1, width=0, spot_type="standard", level=""
    )

    assert spots == []


@pytest.mark.asyncio
async def test_list_spots_filters_by_type_and_activity() -> None:
    service, _, _, _ = _service()
    garage_id = await _garage(service)
    created = await service.add_spots(
        garage_id,
        [
            NewSpot(code="A1", spot_type="standard", level=""),
            NewSpot(code="A2", spot_type="ev", level=""),
            NewSpot(code="A3", spot_type="ev", level=""),
        ],
    )
    await service.update_spot(created[2].spot_id, SpotPatch(is_active=False))

    ev_active = await service.list_spots(garage_id, spot_type="ev", include_inactive=False)
    ev_all = await service.list_spots(garage_id, spot_type="ev", include_inactive=True)

    assert [s.code for s in ev_active] == ["A2"]
    assert [s.code for s in ev_all] == ["A2", "A3"]


@pytest.mark.asyncio
async def test_deactivating_a_spot_with_open_reservations_is_refused() -> None:
    service, _, _, spot_repo = _service()
    garage_id = await _garage(service)
    [spot] = await service.add_spots(garage_id, [NewSpot(code="A1", spot_type="standard", level="")])
    spot_repo.open_reservations[spot.spot_id] = 2

    with pytest.raises(SpotHasActiveReservations) as excinfo:
        await service.update_spot(spot.spot_id, SpotPatch(is_active=False))

    assert excinfo.value.count == 2
    assert (await service.get_spot(spot.spot_id)).is_active


@pytest.mark.asyncio
async def test_open_reservations_do_not_block_other_spot_changes() -> None:
    service, _, _, spot_repo = _service()
    garage_id = await _garage(service)
    [spot] = await service.add_spots(garage_id, [NewSpot(code="A1", spot_type="standard", level="")])
    spot_repo.open_reservations[spot.spot_id] = 1

    updated = await service.update_spot(spot.spot_id, SpotPatch(spot_type="ev", level="L3"))

    assert updated.spot_type == "ev"
    assert updated.level == "L3"
    assert updated.is_active


@pytest.mark.asyncio
async def test_update_spot_rejects_an_unknown_type() -> None:
    service, _, _, _ = _service()
    garage_id = await _garage(service)
    [spot] = await service.add_spots(garage_id, [NewSpot(code="A1", spot_type="standard", level="")])

    with pytest.raises(UnknownSpotType):
        await service.update_spot(spot.spot_id, SpotPatch(spot_type="helipad"))


@pytest.mark.asyncio
async def test_update_unknown_spot_raises_not_found() -> None:
    service, _, _, _ = _service()

    with pytest.raises(SpotNotFound):
        await service.update_spot(404, SpotPatch(level="L1"))


@pytest.mark.asyncio
async def test_get_unknown_spot_raises_not_found() -> None:
    service, _, _, _ = _service()

    with pytest.raises(SpotNotFound):
        await service.get_spot(404)


@pytest.mark.asyncio
async def test_list_spot_types_passes_through_the_catalog() -> None:
    service, _, _, _ = _service()

    types = await service.list_spot_types()

    assert [t.code for t in types] == ["standard", "compact", "ev"]
