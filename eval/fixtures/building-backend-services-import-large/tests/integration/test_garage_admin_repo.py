"""Integration tier for garage administration: operators, garages,
opening hours and spots against the real schema (unique constraints,
foreign keys, the seeded spot types)."""

from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest
from psycopg_pool import AsyncConnectionPool

from app.domain.errors import DuplicateOperator, DuplicateSpotCode, OperatorNotFound, UnknownSpotType
from app.domain.garages import DailyHours, GaragePatch, NewSpot, SpotPatch
from app.domain.models import TimeWindow
from app.repo.garage_admin_repo import GarageAdminRepo
from app.repo.operator_repo import OperatorRepo
from app.repo.reservation_repo import ReservationRepo
from app.repo.spot_repo import SpotRepo
from tests.integration.helpers import seed_operator, seed_operator_garage

pytestmark = pytest.mark.integration

NOW = datetime(2026, 8, 15, 12, tzinfo=UTC)


@pytest.mark.asyncio
async def test_create_and_get_operator(pool: AsyncConnectionPool) -> None:
    repo = OperatorRepo(pool)

    created = await repo.create(name="Harbour Parking", contact_email="ops@harbour.example", now=NOW)
    fetched = await repo.get(created.operator_id)

    assert fetched == created
    assert fetched.created_at == NOW


@pytest.mark.asyncio
async def test_operator_names_are_unique(pool: AsyncConnectionPool) -> None:
    repo = OperatorRepo(pool)
    await repo.create(name="Harbour Parking", contact_email="a@example.com", now=NOW)

    with pytest.raises(DuplicateOperator):
        await repo.create(name="Harbour Parking", contact_email="b@example.com", now=NOW)


@pytest.mark.asyncio
async def test_list_operators_is_ordered_by_name_and_paged(pool: AsyncConnectionPool) -> None:
    repo = OperatorRepo(pool)
    for name in ("Zeta", "Alpha", "Mid"):
        await repo.create(name=name, contact_email="x@example.com", now=NOW)

    first_page = await repo.list(limit=2, offset=0)
    second_page = await repo.list(limit=2, offset=2)

    assert [o.name for o in first_page] == ["Alpha", "Mid"]
    assert [o.name for o in second_page] == ["Zeta"]


@pytest.mark.asyncio
async def test_update_operator_leaves_omitted_fields_unchanged(pool: AsyncConnectionPool) -> None:
    repo = OperatorRepo(pool)
    created = await repo.create(name="Harbour", contact_email="old@example.com", now=NOW)

    updated = await repo.update(
        operator_id=created.operator_id, name=None, contact_email="new@example.com", now=NOW + timedelta(hours=1)
    )

    assert updated.name == "Harbour"
    assert updated.contact_email == "new@example.com"
    assert updated.updated_at == NOW + timedelta(hours=1)


@pytest.mark.asyncio
async def test_update_unknown_operator_returns_none(pool: AsyncConnectionPool) -> None:
    result = await OperatorRepo(pool).update(operator_id=999, name="x", contact_email=None, now=NOW)

    assert result is None


@pytest.mark.asyncio
async def test_create_garage_for_unknown_operator_is_rejected(pool: AsyncConnectionPool) -> None:
    with pytest.raises(OperatorNotFound):
        await GarageAdminRepo(pool).create(
            operator_id=404, name="Nowhere", address="", timezone="UTC", now=NOW
        )


@pytest.mark.asyncio
async def test_create_garage_defaults_to_active(pool: AsyncConnectionPool) -> None:
    operator_id = await seed_operator(pool)
    repo = GarageAdminRepo(pool)

    garage = await repo.create(
        operator_id=operator_id, name="Station", address="1 Station Rd", timezone="Europe/London", now=NOW
    )

    assert garage.is_active
    assert garage.operator_id == operator_id
    assert (await repo.get(garage.garage_id)) == garage


@pytest.mark.asyncio
async def test_list_by_operator_hides_inactive_unless_asked(pool: AsyncConnectionPool) -> None:
    operator_id = await seed_operator(pool)
    other_operator = await seed_operator(pool, name="Other")
    active = await seed_operator_garage(pool, operator_id, name="Active")
    closed = await seed_operator_garage(pool, operator_id, name="Closed")
    await seed_operator_garage(pool, other_operator, name="Elsewhere")
    repo = GarageAdminRepo(pool)
    await repo.update(garage_id=closed, patch=GaragePatch(is_active=False), now=NOW)

    visible = await repo.list_by_operator(operator_id, include_inactive=False)
    everything = await repo.list_by_operator(operator_id, include_inactive=True)

    assert [g.garage_id for g in visible] == [active]
    assert {g.garage_id for g in everything} == {active, closed}


@pytest.mark.asyncio
async def test_update_garage_is_partial(pool: AsyncConnectionPool) -> None:
    operator_id = await seed_operator(pool)
    garage_id = await seed_operator_garage(pool, operator_id, name="Before", timezone="UTC")
    repo = GarageAdminRepo(pool)

    updated = await repo.update(
        garage_id=garage_id, patch=GaragePatch(timezone="Europe/Paris"), now=NOW
    )

    assert updated.name == "Before"
    assert updated.timezone == "Europe/Paris"
    assert updated.updated_at == NOW


@pytest.mark.asyncio
async def test_update_unknown_garage_returns_none(pool: AsyncConnectionPool) -> None:
    result = await GarageAdminRepo(pool).update(garage_id=999, patch=GaragePatch(name="x"), now=NOW)

    assert result is None


@pytest.mark.asyncio
async def test_replace_opening_hours_replaces_the_whole_week(pool: AsyncConnectionPool) -> None:
    operator_id = await seed_operator(pool)
    garage_id = await seed_operator_garage(pool, operator_id)
    repo = GarageAdminRepo(pool)
    await repo.replace_opening_hours(
        garage_id,
        (DailyHours(weekday=0, open_minute=420, close_minute=1320), DailyHours(weekday=1, open_minute=420, close_minute=1320)),
    )

    await repo.replace_opening_hours(garage_id, (DailyHours(weekday=5, open_minute=0, close_minute=1440),))
    hours = await repo.get_opening_hours(garage_id)

    assert hours.days == (DailyHours(weekday=5, open_minute=0, close_minute=1440),)


@pytest.mark.asyncio
async def test_opening_hours_violating_the_check_constraint_leave_the_old_week(pool: AsyncConnectionPool) -> None:
    operator_id = await seed_operator(pool)
    garage_id = await seed_operator_garage(pool, operator_id)
    repo = GarageAdminRepo(pool)
    original = (DailyHours(weekday=0, open_minute=420, close_minute=1320),)
    await repo.replace_opening_hours(garage_id, original)

    with pytest.raises(Exception):
        await repo.replace_opening_hours(garage_id, (DailyHours(weekday=2, open_minute=600, close_minute=500),))

    assert (await repo.get_opening_hours(garage_id)).days == original


@pytest.mark.asyncio
async def test_seeded_spot_types_are_listed(pool: AsyncConnectionPool) -> None:
    types = await SpotRepo(pool).list_spot_types()

    assert [t.code for t in types] == ["standard", "compact", "ev", "accessible", "motorcycle"]


@pytest.mark.asyncio
async def test_create_many_spots_returns_them_with_type_codes(pool: AsyncConnectionPool) -> None:
    operator_id = await seed_operator(pool)
    garage_id = await seed_operator_garage(pool, operator_id)
    repo = SpotRepo(pool)

    spots = await repo.create_many(
        garage_id=garage_id,
        spots=[NewSpot(code="A1", spot_type="standard", level="L1"), NewSpot(code="E1", spot_type="ev", level="L1")],
        now=NOW,
    )

    assert [(s.code, s.spot_type, s.is_active) for s in spots] == [("A1", "standard", True), ("E1", "ev", True)]


@pytest.mark.asyncio
async def test_create_many_with_a_duplicate_code_rolls_back_the_batch(pool: AsyncConnectionPool) -> None:
    operator_id = await seed_operator(pool)
    garage_id = await seed_operator_garage(pool, operator_id)
    repo = SpotRepo(pool)
    await repo.create_many(garage_id=garage_id, spots=[NewSpot(code="A2", spot_type="standard", level="")], now=NOW)

    with pytest.raises(DuplicateSpotCode) as excinfo:
        await repo.create_many(
            garage_id=garage_id,
            spots=[NewSpot(code="A1", spot_type="standard", level=""), NewSpot(code="A2", spot_type="standard", level="")],
            now=NOW,
        )

    assert excinfo.value.code == "A2"
    codes = [s.code for s in await repo.list_by_garage(garage_id, spot_type=None, include_inactive=True)]
    assert codes == ["A2"]


@pytest.mark.asyncio
async def test_create_many_with_an_unknown_type_rolls_back_the_batch(pool: AsyncConnectionPool) -> None:
    operator_id = await seed_operator(pool)
    garage_id = await seed_operator_garage(pool, operator_id)
    repo = SpotRepo(pool)

    with pytest.raises(UnknownSpotType):
        await repo.create_many(
            garage_id=garage_id,
            spots=[NewSpot(code="A1", spot_type="standard", level=""), NewSpot(code="A2", spot_type="hover", level="")],
            now=NOW,
        )

    assert await repo.list_by_garage(garage_id, spot_type=None, include_inactive=True) == []


@pytest.mark.asyncio
async def test_list_by_garage_filters_by_type_and_active_flag(pool: AsyncConnectionPool) -> None:
    operator_id = await seed_operator(pool)
    garage_id = await seed_operator_garage(pool, operator_id)
    repo = SpotRepo(pool)
    a1, e1, e2 = await repo.create_many(
        garage_id=garage_id,
        spots=[
            NewSpot(code="A1", spot_type="standard", level="L1"),
            NewSpot(code="E1", spot_type="ev", level="L1"),
            NewSpot(code="E2", spot_type="ev", level="L2"),
        ],
        now=NOW,
    )
    await repo.update(spot_id=e2.spot_id, patch=SpotPatch(is_active=False), now=NOW)

    ev_active = await repo.list_by_garage(garage_id, spot_type="ev", include_inactive=False)
    ev_all = await repo.list_by_garage(garage_id, spot_type="ev", include_inactive=True)
    everything = await repo.list_by_garage(garage_id, spot_type=None, include_inactive=False)

    assert [s.spot_id for s in ev_active] == [e1.spot_id]
    assert {s.spot_id for s in ev_all} == {e1.spot_id, e2.spot_id}
    assert {s.spot_id for s in everything} == {a1.spot_id, e1.spot_id}


@pytest.mark.asyncio
async def test_update_spot_changes_type_and_level(pool: AsyncConnectionPool) -> None:
    operator_id = await seed_operator(pool)
    garage_id = await seed_operator_garage(pool, operator_id)
    repo = SpotRepo(pool)
    (spot,) = await repo.create_many(
        garage_id=garage_id, spots=[NewSpot(code="A1", spot_type="standard", level="L1")], now=NOW
    )

    updated = await repo.update(
        spot_id=spot.spot_id, patch=SpotPatch(spot_type="accessible", level="L0"), now=NOW + timedelta(minutes=5)
    )

    assert updated.spot_type == "accessible"
    assert updated.level == "L0"
    assert updated.is_active
    assert updated.updated_at == NOW + timedelta(minutes=5)


@pytest.mark.asyncio
async def test_update_unknown_spot_returns_none(pool: AsyncConnectionPool) -> None:
    assert await SpotRepo(pool).update(spot_id=999, patch=SpotPatch(level="L9"), now=NOW) is None


@pytest.mark.asyncio
async def test_inactive_spots_are_not_offered_for_new_reservations(pool: AsyncConnectionPool) -> None:
    operator_id = await seed_operator(pool)
    garage_id = await seed_operator_garage(pool, operator_id)
    spots = SpotRepo(pool)
    a1, a2 = await spots.create_many(
        garage_id=garage_id,
        spots=[NewSpot(code="A1", spot_type="standard", level=""), NewSpot(code="A2", spot_type="standard", level="")],
        now=NOW,
    )
    await spots.update(spot_id=a1.spot_id, patch=SpotPatch(is_active=False), now=NOW)

    reservation = await ReservationRepo(pool).create_reservation(
        public_id=uuid4(), garage_id=garage_id, driver_id=1, window=TimeWindow(start=NOW, end=NOW + timedelta(hours=1))
    )

    assert reservation.spot_id == a2.spot_id


@pytest.mark.asyncio
async def test_count_open_reservations_ignores_ended_and_cancelled(pool: AsyncConnectionPool) -> None:
    operator_id = await seed_operator(pool)
    garage_id = await seed_operator_garage(pool, operator_id)
    spots = SpotRepo(pool)
    (spot,) = await spots.create_many(
        garage_id=garage_id, spots=[NewSpot(code="A1", spot_type="standard", level="")], now=NOW
    )
    reservations = ReservationRepo(pool)
    await reservations.create_reservation(
        public_id=uuid4(), garage_id=garage_id, driver_id=1,
        window=TimeWindow(start=NOW - timedelta(hours=5), end=NOW - timedelta(hours=4)),
    )
    upcoming = await reservations.create_reservation(
        public_id=uuid4(), garage_id=garage_id, driver_id=2,
        window=TimeWindow(start=NOW + timedelta(hours=1), end=NOW + timedelta(hours=2)),
    )
    cancelled = await reservations.create_reservation(
        public_id=uuid4(), garage_id=garage_id, driver_id=3,
        window=TimeWindow(start=NOW + timedelta(hours=3), end=NOW + timedelta(hours=4)),
    )
    await reservations.cancel(public_id=cancelled.public_id, now=NOW)

    count = await spots.count_open_reservations(spot_id=spot.spot_id, now=NOW)

    assert count == 1
    assert upcoming.spot_id == spot.spot_id


@pytest.mark.asyncio
async def test_count_active_spots(pool: AsyncConnectionPool) -> None:
    operator_id = await seed_operator(pool)
    garage_id = await seed_operator_garage(pool, operator_id)
    spots = SpotRepo(pool)
    created = await spots.create_many(
        garage_id=garage_id,
        spots=[NewSpot(code=f"A{n}", spot_type="standard", level="") for n in range(1, 4)],
        now=NOW,
    )
    await spots.update(spot_id=created[0].spot_id, patch=SpotPatch(is_active=False), now=NOW)

    assert await spots.count_active(garage_id) == 2
