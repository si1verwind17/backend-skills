"""Every HTTP route the service exposes, registered in one place.

  /healthz, /v1/reservations..., /v1/drivers/{id}/reservations,
  /v1/garages/{id}/reservations, /internal/outbox/publish   -> routes.py
  /v1/admin/operators..., /v1/admin/garages..., /v1/admin/spots...,
  /v1/admin/spot-types                                      -> garage_routes.py
  /v1/admin/.../tariffs, /v1/garages/{id}/quotes, /v1/quotes/{id},
  /v1/reservations/{id}/charge, /internal/pricing/settle    -> pricing_routes.py
  /v1/drivers, /v1/drivers/{id}, /v1/drivers/{id}/vehicles  -> driver_routes.py
  /v1/admin/.../reports/...                                 -> report_routes.py
  /internal/notifications/...                               -> notification_routes.py
"""

from __future__ import annotations

from fastapi import APIRouter

from app.api import (
    driver_routes,
    garage_routes,
    notification_routes,
    pricing_routes,
    report_routes,
    routes,
)

api_router = APIRouter()
api_router.include_router(routes.router)
api_router.include_router(garage_routes.router)
api_router.include_router(pricing_routes.router)
api_router.include_router(driver_routes.router)
api_router.include_router(report_routes.router)
api_router.include_router(notification_routes.router)
