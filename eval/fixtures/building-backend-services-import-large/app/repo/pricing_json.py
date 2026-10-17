"""JSON (de)serialization of price breakdowns for the quote.breakdown
jsonb column. Kept in the repo layer: the stored shape is a storage
detail, separate from the HTTP response shape in app/api/pricing_schemas.py."""

from __future__ import annotations

from datetime import date
from typing import Any

from app.domain.pricing import PriceBreakdown, PriceDay, PriceLine


def breakdown_to_json(breakdown: PriceBreakdown) -> dict[str, Any]:
    return {
        "tariff_id": breakdown.tariff_id,
        "currency": breakdown.currency,
        "total_cents": breakdown.total_cents,
        "grace_applied": breakdown.grace_applied,
        "days": [
            {
                "local_date": d.local_date.isoformat(),
                "uncapped_cents": d.uncapped_cents,
                "charged_cents": d.charged_cents,
            }
            for d in breakdown.days
        ],
        "lines": [
            {
                "local_date": line.local_date.isoformat(),
                "start_minute": line.start_minute,
                "end_minute": line.end_minute,
                "minutes": line.minutes,
                "blocks": line.blocks,
                "rate_cents_per_block": line.rate_cents_per_block,
                "amount_cents": line.amount_cents,
            }
            for line in breakdown.lines
        ],
    }


def breakdown_from_json(data: dict[str, Any]) -> PriceBreakdown:
    return PriceBreakdown(
        tariff_id=data["tariff_id"],
        currency=data["currency"],
        total_cents=data["total_cents"],
        grace_applied=data["grace_applied"],
        days=tuple(
            PriceDay(
                local_date=date.fromisoformat(d["local_date"]),
                uncapped_cents=d["uncapped_cents"],
                charged_cents=d["charged_cents"],
            )
            for d in data["days"]
        ),
        lines=tuple(
            PriceLine(
                local_date=date.fromisoformat(line["local_date"]),
                start_minute=line["start_minute"],
                end_minute=line["end_minute"],
                minutes=line["minutes"],
                blocks=line["blocks"],
                rate_cents_per_block=line["rate_cents_per_block"],
                amount_cents=line["amount_cents"],
            )
            for line in data["lines"]
        ),
    )
