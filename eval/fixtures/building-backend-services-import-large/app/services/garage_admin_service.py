"""Garage and spot administration for operators: operators, garages,
weekly opening hours, spot types and spots. Validation rules are pure
functions in app/domain/garages.py; this module sequences them with the
repo calls and turns missing rows into domain errors."""

from __future__ import annotations

from app.domain.errors import (
    DuplicateSpotCode,
    GarageNotFound,
    OperatorNotFound,
    SpotHasActiveReservations,
    SpotNotFound,
    UnknownSpotType,
)
from app.domain.garages import (
    DailyHours,
    GarageDetails,
    GaragePatch,
    NewSpot,
    Operator,
    Spot,
    SpotPatch,
    SpotType,
    WeeklyHours,
    normalize_spot_code,
    spot_codes_in_range,
    validate_timezone,
    validate_weekly_hours,
)
from app.domain.ports import Clock
from app.repo.garage_admin_repo import GarageAdminRepo
from app.repo.operator_repo import OperatorRepo
from app.repo.spot_repo import SpotRepo

MAX_SPOTS_PER_REQUEST = 500


class GarageAdminService:
    def __init__(
        self,
        operator_repo: OperatorRepo,
        garage_repo: GarageAdminRepo,
        spot_repo: SpotRepo,
        clock: Clock,
    ) -> None:
        self._operators = operator_repo
        self._garages = garage_repo
        self._spots = spot_repo
        self._clock = clock

    # --- operators -------------------------------------------------------

    async def create_operator(self, *, name: str, contact_email: str) -> Operator:
        return await self._operators.create(
            name=name.strip(), contact_email=contact_email.strip(), now=self._clock.now()
        )

    async def get_operator(self, operator_id: int) -> Operator:
        operator = await self._operators.get(operator_id)
        if operator is None:
            raise OperatorNotFound(operator_id=operator_id)
        return operator

    async def list_operators(self, *, limit: int, offset: int) -> list[Operator]:
        return await self._operators.list(limit=limit, offset=offset)

    async def update_operator(
        self, operator_id: int, *, name: str | None, contact_email: str | None
    ) -> Operator:
        operator = await self._operators.update(
            operator_id=operator_id,
            name=name.strip() if name is not None else None,
            contact_email=contact_email.strip() if contact_email is not None else None,
            now=self._clock.now(),
        )
        if operator is None:
            raise OperatorNotFound(operator_id=operator_id)
        return operator

    # --- garages ---------------------------------------------------------

    async def create_garage(
        self, *, operator_id: int, name: str, address: str, timezone: str
    ) -> GarageDetails:
        validate_timezone(timezone)
        return await self._garages.create(
            operator_id=operator_id,
            name=name.strip(),
            address=address.strip(),
            timezone=timezone,
            now=self._clock.now(),
        )

    async def get_garage(self, garage_id: int) -> GarageDetails:
        garage = await self._garages.get(garage_id)
        if garage is None:
            raise GarageNotFound(garage_id=garage_id)
        return garage

    async def list_garages(self, operator_id: int, *, include_inactive: bool) -> list[GarageDetails]:
        await self.get_operator(operator_id)
        return await self._garages.list_by_operator(operator_id, include_inactive=include_inactive)

    async def update_garage(self, garage_id: int, patch: GaragePatch) -> GarageDetails:
        if patch.timezone is not None:
            validate_timezone(patch.timezone)
        garage = await self._garages.update(garage_id=garage_id, patch=patch, now=self._clock.now())
        if garage is None:
            raise GarageNotFound(garage_id=garage_id)
        return garage

    async def get_opening_hours(self, garage_id: int) -> WeeklyHours:
        await self.get_garage(garage_id)
        return await self._garages.get_opening_hours(garage_id)

    async def set_opening_hours(self, garage_id: int, days: list[DailyHours]) -> WeeklyHours:
        validated = validate_weekly_hours(days)
        await self.get_garage(garage_id)
        return await self._garages.replace_opening_hours(garage_id, validated)

    # --- spots -----------------------------------------------------------

    async def list_spot_types(self) -> list[SpotType]:
        return await self._spots.list_spot_types()

    async def add_spots(self, garage_id: int, spots: list[NewSpot]) -> list[Spot]:
        """Bulk add. Codes are normalized first; a code repeated within
        the request is rejected before touching the database."""
        await self.get_garage(garage_id)
        await self._require_spot_types({s.spot_type for s in spots})
        normalized: list[NewSpot] = []
        seen: set[str] = set()
        for spot in spots:
            code = normalize_spot_code(spot.code)
            if code in seen:
                raise DuplicateSpotCode(garage_id=garage_id, code=code)
            seen.add(code)
            normalized.append(NewSpot(code=code, spot_type=spot.spot_type, level=spot.level.strip()))
        return await self._spots.create_many(garage_id=garage_id, spots=normalized, now=self._clock.now())

    async def add_spot_range(
        self,
        garage_id: int,
        *,
        prefix: str,
        first: int,
        last: int,
        width: int,
        spot_type: str,
        level: str,
    ) -> list[Spot]:
        codes = spot_codes_in_range(prefix, first, last, width)
        return await self.add_spots(
            garage_id, [NewSpot(code=code, spot_type=spot_type, level=level) for code in codes]
        )

    async def list_spots(
        self, garage_id: int, *, spot_type: str | None, include_inactive: bool
    ) -> list[Spot]:
        await self.get_garage(garage_id)
        return await self._spots.list_by_garage(
            garage_id, spot_type=spot_type, include_inactive=include_inactive
        )

    async def update_spot(self, spot_id: int, patch: SpotPatch) -> Spot:
        """Taking a spot out of service is refused while it still holds
        reservations that have not ended: those drivers were promised that
        spot, and moving them is a staff decision, not an automatic one."""
        now = self._clock.now()
        if patch.spot_type is not None:
            await self._require_spot_types({patch.spot_type})
        if patch.is_active is False:
            open_count = await self._spots.count_open_reservations(spot_id=spot_id, now=now)
            if open_count:
                raise SpotHasActiveReservations(spot_id=spot_id, count=open_count)
        spot = await self._spots.update(spot_id=spot_id, patch=patch, now=now)
        if spot is None:
            raise SpotNotFound(spot_id=spot_id)
        return spot

    async def get_spot(self, spot_id: int) -> Spot:
        spot = await self._spots.get(spot_id)
        if spot is None:
            raise SpotNotFound(spot_id=spot_id)
        return spot

    async def _require_spot_types(self, codes: set[str]) -> None:
        known = {t.code for t in await self._spots.list_spot_types()}
        for code in sorted(codes):
            if code not in known:
                raise UnknownSpotType(code=code)
