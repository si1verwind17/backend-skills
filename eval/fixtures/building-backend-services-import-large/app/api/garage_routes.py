"""HTTP routes for operator administration of garages and spots. Request
/response mapping only; rules live in app/domain/garages.py and
app/services/garage_admin_service.py.

These endpoints sit under /v1/admin and are expected to be reachable only
through the operator console's gateway route, which authenticates staff
before forwarding.
"""

from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, Query

from app.api.deps import get_garage_admin_service
from app.api.garage_schemas import (
    GarageCreateRequest,
    GarageResponse,
    GarageUpdateRequest,
    OpeningHoursRequest,
    OpeningHoursResponse,
    OperatorCreateRequest,
    OperatorResponse,
    OperatorUpdateRequest,
    SpotRangeCreateRequest,
    SpotResponse,
    SpotsCreateRequest,
    SpotTypeResponse,
    SpotUpdateRequest,
)
from app.domain.garages import NewSpot
from app.services.garage_admin_service import GarageAdminService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/v1/admin", tags=["admin"])


# --- operators ---------------------------------------------------------------


@router.post("/operators", response_model=OperatorResponse, status_code=201)
async def create_operator(
    body: OperatorCreateRequest, service: GarageAdminService = Depends(get_garage_admin_service)
) -> OperatorResponse:
    operator = await service.create_operator(name=body.name, contact_email=body.contact_email)
    logger.info("operator created", extra={"operator_id": operator.operator_id})
    return OperatorResponse.from_domain(operator)


@router.get("/operators", response_model=list[OperatorResponse])
async def list_operators(
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    service: GarageAdminService = Depends(get_garage_admin_service),
) -> list[OperatorResponse]:
    operators = await service.list_operators(limit=limit, offset=offset)
    return [OperatorResponse.from_domain(o) for o in operators]


@router.get("/operators/{operator_id}", response_model=OperatorResponse)
async def get_operator(
    operator_id: int, service: GarageAdminService = Depends(get_garage_admin_service)
) -> OperatorResponse:
    return OperatorResponse.from_domain(await service.get_operator(operator_id))


@router.patch("/operators/{operator_id}", response_model=OperatorResponse)
async def update_operator(
    operator_id: int,
    body: OperatorUpdateRequest,
    service: GarageAdminService = Depends(get_garage_admin_service),
) -> OperatorResponse:
    operator = await service.update_operator(operator_id, name=body.name, contact_email=body.contact_email)
    logger.info("operator updated", extra={"operator_id": operator_id})
    return OperatorResponse.from_domain(operator)


@router.get("/operators/{operator_id}/garages", response_model=list[GarageResponse])
async def list_operator_garages(
    operator_id: int,
    include_inactive: bool = False,
    service: GarageAdminService = Depends(get_garage_admin_service),
) -> list[GarageResponse]:
    garages = await service.list_garages(operator_id, include_inactive=include_inactive)
    return [GarageResponse.from_domain(g) for g in garages]


# --- garages -----------------------------------------------------------------


@router.post("/garages", response_model=GarageResponse, status_code=201)
async def create_garage(
    body: GarageCreateRequest, service: GarageAdminService = Depends(get_garage_admin_service)
) -> GarageResponse:
    garage = await service.create_garage(
        operator_id=body.operator_id, name=body.name, address=body.address, timezone=body.timezone
    )
    logger.info("garage created", extra={"garage_id": garage.garage_id, "operator_id": body.operator_id})
    return GarageResponse.from_domain(garage)


@router.get("/garages/{garage_id}", response_model=GarageResponse)
async def get_garage(
    garage_id: int, service: GarageAdminService = Depends(get_garage_admin_service)
) -> GarageResponse:
    return GarageResponse.from_domain(await service.get_garage(garage_id))


@router.patch("/garages/{garage_id}", response_model=GarageResponse)
async def update_garage(
    garage_id: int,
    body: GarageUpdateRequest,
    service: GarageAdminService = Depends(get_garage_admin_service),
) -> GarageResponse:
    garage = await service.update_garage(garage_id, body.to_patch())
    logger.info("garage updated", extra={"garage_id": garage_id})
    return GarageResponse.from_domain(garage)


@router.get("/garages/{garage_id}/opening-hours", response_model=OpeningHoursResponse)
async def get_opening_hours(
    garage_id: int, service: GarageAdminService = Depends(get_garage_admin_service)
) -> OpeningHoursResponse:
    return OpeningHoursResponse.from_domain(await service.get_opening_hours(garage_id))


@router.put("/garages/{garage_id}/opening-hours", response_model=OpeningHoursResponse)
async def set_opening_hours(
    garage_id: int,
    body: OpeningHoursRequest,
    service: GarageAdminService = Depends(get_garage_admin_service),
) -> OpeningHoursResponse:
    hours = await service.set_opening_hours(garage_id, [d.to_domain() for d in body.days])
    logger.info("opening hours replaced", extra={"garage_id": garage_id, "days": len(hours.days)})
    return OpeningHoursResponse.from_domain(hours)


# --- spots -------------------------------------------------------------------


@router.get("/spot-types", response_model=list[SpotTypeResponse])
async def list_spot_types(
    service: GarageAdminService = Depends(get_garage_admin_service),
) -> list[SpotTypeResponse]:
    return [SpotTypeResponse.from_domain(t) for t in await service.list_spot_types()]


@router.get("/garages/{garage_id}/spots", response_model=list[SpotResponse])
async def list_spots(
    garage_id: int,
    spot_type: str | None = None,
    include_inactive: bool = False,
    service: GarageAdminService = Depends(get_garage_admin_service),
) -> list[SpotResponse]:
    spots = await service.list_spots(garage_id, spot_type=spot_type, include_inactive=include_inactive)
    return [SpotResponse.from_domain(s) for s in spots]


@router.post("/garages/{garage_id}/spots", response_model=list[SpotResponse], status_code=201)
async def create_spots(
    garage_id: int,
    body: SpotsCreateRequest,
    service: GarageAdminService = Depends(get_garage_admin_service),
) -> list[SpotResponse]:
    spots = await service.add_spots(
        garage_id,
        [NewSpot(code=s.code, spot_type=s.spot_type, level=s.level) for s in body.spots],
    )
    logger.info("spots created", extra={"garage_id": garage_id, "count": len(spots)})
    return [SpotResponse.from_domain(s) for s in spots]


@router.post("/garages/{garage_id}/spots/range", response_model=list[SpotResponse], status_code=201)
async def create_spot_range(
    garage_id: int,
    body: SpotRangeCreateRequest,
    service: GarageAdminService = Depends(get_garage_admin_service),
) -> list[SpotResponse]:
    spots = await service.add_spot_range(
        garage_id,
        prefix=body.prefix,
        first=body.first,
        last=body.last,
        width=body.width,
        spot_type=body.spot_type,
        level=body.level,
    )
    logger.info("spot range created", extra={"garage_id": garage_id, "count": len(spots)})
    return [SpotResponse.from_domain(s) for s in spots]


@router.get("/spots/{spot_id}", response_model=SpotResponse)
async def get_spot(
    spot_id: int, service: GarageAdminService = Depends(get_garage_admin_service)
) -> SpotResponse:
    return SpotResponse.from_domain(await service.get_spot(spot_id))


@router.patch("/spots/{spot_id}", response_model=SpotResponse)
async def update_spot(
    spot_id: int,
    body: SpotUpdateRequest,
    service: GarageAdminService = Depends(get_garage_admin_service),
) -> SpotResponse:
    spot = await service.update_spot(spot_id, body.to_patch())
    logger.info("spot updated", extra={"spot_id": spot_id, "is_active": spot.is_active})
    return SpotResponse.from_domain(spot)
