"""HTTP routes for driver accounts and saved vehicles (mobile app). Like
the reservation routes, these trust the driver_id in the path; the
gateway in front of the service checks it against the signed-in driver.
"""

from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, Response

from app.api.deps import get_driver_service
from app.api.driver_schemas import (
    DriverCreateRequest,
    DriverResponse,
    DriverUpdateRequest,
    VehicleCreateRequest,
    VehicleResponse,
)
from app.services.driver_service import DriverService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/v1/drivers", tags=["drivers"])


@router.post("", response_model=DriverResponse, status_code=201)
async def register_driver(
    body: DriverCreateRequest, service: DriverService = Depends(get_driver_service)
) -> DriverResponse:
    driver = await service.register(
        driver_id=body.driver_id,
        display_name=body.display_name,
        email=body.email,
        phone=body.phone,
        notify_reminders=body.notify_reminders,
    )
    logger.info("driver registered", extra={"driver_id": driver.driver_id})
    return DriverResponse.from_domain(driver)


@router.get("/{driver_id}", response_model=DriverResponse)
async def get_driver(driver_id: int, service: DriverService = Depends(get_driver_service)) -> DriverResponse:
    return DriverResponse.from_domain(await service.get(driver_id))


@router.patch("/{driver_id}", response_model=DriverResponse)
async def update_driver(
    driver_id: int,
    body: DriverUpdateRequest,
    service: DriverService = Depends(get_driver_service),
) -> DriverResponse:
    driver = await service.update(driver_id, body.to_patch())
    logger.info("driver updated", extra={"driver_id": driver_id})
    return DriverResponse.from_domain(driver)


@router.get("/{driver_id}/vehicles", response_model=list[VehicleResponse])
async def list_vehicles(
    driver_id: int, service: DriverService = Depends(get_driver_service)
) -> list[VehicleResponse]:
    return [VehicleResponse.from_domain(v) for v in await service.list_vehicles(driver_id)]


@router.post("/{driver_id}/vehicles", response_model=VehicleResponse, status_code=201)
async def add_vehicle(
    driver_id: int,
    body: VehicleCreateRequest,
    service: DriverService = Depends(get_driver_service),
) -> VehicleResponse:
    vehicle = await service.add_vehicle(
        driver_id, country_code=body.country_code, plate=body.plate, nickname=body.nickname
    )
    logger.info("vehicle added", extra={"driver_id": driver_id, "vehicle_id": vehicle.vehicle_id})
    return VehicleResponse.from_domain(vehicle)


@router.delete("/{driver_id}/vehicles/{vehicle_id}", status_code=204)
async def remove_vehicle(
    driver_id: int, vehicle_id: int, service: DriverService = Depends(get_driver_service)
) -> Response:
    await service.remove_vehicle(driver_id, vehicle_id)
    logger.info("vehicle removed", extra={"driver_id": driver_id, "vehicle_id": vehicle_id})
    return Response(status_code=204)


@router.post("/{driver_id}/vehicles/{vehicle_id}/default", response_model=VehicleResponse)
async def make_default_vehicle(
    driver_id: int, vehicle_id: int, service: DriverService = Depends(get_driver_service)
) -> VehicleResponse:
    vehicle = await service.make_default_vehicle(driver_id, vehicle_id)
    logger.info("default vehicle changed", extra={"driver_id": driver_id, "vehicle_id": vehicle_id})
    return VehicleResponse.from_domain(vehicle)
