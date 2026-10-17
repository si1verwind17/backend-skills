"""HTTP routes for tariffs (operator admin), price quotes (mobile app),
reservation charges, and the scheduled settlement run."""

from __future__ import annotations

import logging
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request, status

from app.api.deps import get_pricing_service, get_settlement_service
from app.api.internal_auth import require_internal_caller
from app.api.pricing_schemas import (
    ChargeResponse,
    QuoteRequest,
    QuoteResponse,
    SettlementRunResponse,
    TariffCloseRequest,
    TariffCreateRequest,
    TariffResponse,
)
from app.domain.models import TimeWindow
from app.services.pricing_service import PricingService
from app.services.settlement_service import SettlementService

logger = logging.getLogger(__name__)

router = APIRouter(tags=["pricing"])


# --- tariffs (operator admin) ----------------------------------------------


@router.post("/v1/admin/garages/{garage_id}/tariffs", response_model=TariffResponse, status_code=201)
async def create_tariff(
    garage_id: int,
    body: TariffCreateRequest,
    service: PricingService = Depends(get_pricing_service),
) -> TariffResponse:
    tariff = await service.create_tariff(body.to_domain(garage_id))
    logger.info(
        "tariff created",
        extra={"garage_id": garage_id, "tariff_id": tariff.tariff_id, "valid_from": str(tariff.valid_from)},
    )
    return TariffResponse.from_domain(tariff)


@router.get("/v1/admin/garages/{garage_id}/tariffs", response_model=list[TariffResponse])
async def list_tariffs(
    garage_id: int, service: PricingService = Depends(get_pricing_service)
) -> list[TariffResponse]:
    return [TariffResponse.from_domain(t) for t in await service.list_tariffs(garage_id)]


@router.get("/v1/admin/tariffs/{tariff_id}", response_model=TariffResponse)
async def get_tariff(tariff_id: int, service: PricingService = Depends(get_pricing_service)) -> TariffResponse:
    return TariffResponse.from_domain(await service.get_tariff(tariff_id))


@router.post("/v1/admin/tariffs/{tariff_id}/close", response_model=TariffResponse)
async def close_tariff(
    tariff_id: int,
    body: TariffCloseRequest,
    service: PricingService = Depends(get_pricing_service),
) -> TariffResponse:
    tariff = await service.close_tariff(tariff_id, valid_to=body.valid_to)
    logger.info("tariff closed", extra={"tariff_id": tariff_id, "valid_to": str(tariff.valid_to)})
    return TariffResponse.from_domain(tariff)


# --- quotes (mobile app) ---------------------------------------------------


@router.post("/v1/garages/{garage_id}/quotes", response_model=QuoteResponse, status_code=201)
async def create_quote(
    garage_id: int,
    body: QuoteRequest,
    service: PricingService = Depends(get_pricing_service),
) -> QuoteResponse:
    quote = await service.create_quote(
        garage_id=garage_id, window=TimeWindow(start=body.window_start, end=body.window_end)
    )
    logger.info(
        "quote created",
        extra={"quote_id": str(quote.public_id), "garage_id": garage_id, "amount_cents": quote.amount_cents},
    )
    return QuoteResponse.from_domain(quote, expired=False)


@router.get("/v1/quotes/{quote_id}", response_model=QuoteResponse)
async def get_quote(quote_id: UUID, service: PricingService = Depends(get_pricing_service)) -> QuoteResponse:
    quote = await service.get_quote(quote_id)
    return QuoteResponse.from_domain(quote, expired=service.is_expired(quote))


# --- charges ---------------------------------------------------------------


@router.get("/v1/reservations/{public_id}/charge", response_model=ChargeResponse)
async def get_reservation_charge(
    public_id: UUID, service: PricingService = Depends(get_pricing_service)
) -> ChargeResponse:
    charge = await service.get_charge(public_id)
    if charge is None:
        # Not an error in the domain sense: the reservation may simply not
        # be completed or settled yet.
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="no charge for this reservation yet")
    return ChargeResponse.from_domain(public_id, charge)


@router.post(
    "/internal/pricing/settle",
    response_model=SettlementRunResponse,
    dependencies=[Depends(require_internal_caller)],
)
async def settle_completed_reservations(
    request: Request, service: SettlementService = Depends(get_settlement_service)
) -> SettlementRunResponse:
    result = await service.run_once(batch_size=request.app.state.settings.settlement_batch_size)
    logger.info(
        "settlement endpoint invoked",
        extra={"claimed": result.claimed, "settled": result.settled, "unpriced": result.unpriced},
    )
    return SettlementRunResponse(
        claimed=result.claimed,
        settled=result.settled,
        unpriced=result.unpriced,
        already_settled=result.already_settled,
    )
