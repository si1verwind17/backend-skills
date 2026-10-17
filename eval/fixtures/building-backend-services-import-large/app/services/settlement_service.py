"""Settles completed reservations into charges, one scheduled run at a
time (Cloud Scheduler -> POST /internal/pricing/settle).

Each completed reservation is priced once, for its charged window (the
booked window, extended to completion time on an overstay), under the
tariff in force on the window's first garage-local date. A reservation
whose garage has no tariff for that date is left unsettled and counted,
so an operator who forgot to set up pricing sees it in the run result
and the logs instead of drivers silently being charged nothing.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import date

from app.domain.ports import Clock
from app.domain.pricing import Tariff
from app.domain.pricing_engine import charged_window, first_local_date, price_window
from app.repo.charge_repo import ChargeRepo
from app.repo.tariff_repo import TariffRepo

logger = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class SettlementRunResult:
    claimed: int
    settled: int
    unpriced: int
    already_settled: int


class SettlementService:
    def __init__(self, charge_repo: ChargeRepo, tariff_repo: TariffRepo, clock: Clock) -> None:
        self._charges = charge_repo
        self._tariffs = tariff_repo
        self._clock = clock

    async def run_once(self, *, batch_size: int) -> SettlementRunResult:
        settled = 0
        unpriced = 0
        already_settled = 0
        # Tariffs looked up during this run, by (garage, local date). A
        # batch is usually dominated by a handful of garages.
        tariffs: dict[tuple[int, date], Tariff | None] = {}

        async with self._charges.claim_unsettled(batch_size) as claim:
            claimed = len(claim.rows)
            for reservation in claim.rows:
                window = charged_window(reservation.window, reservation.completed_at)
                key = (reservation.garage_id, first_local_date(window, reservation.timezone))
                if key not in tariffs:
                    tariffs[key] = await self._tariffs.find_in_force(garage_id=key[0], on_date=key[1])
                tariff = tariffs[key]
                if tariff is None:
                    unpriced += 1
                    logger.warning(
                        "completed reservation left unsettled: no tariff in force",
                        extra={
                            "reservation_id": reservation.reservation_id,
                            "garage_id": reservation.garage_id,
                            "local_date": key[1].isoformat(),
                        },
                    )
                    continue

                breakdown = price_window(window, tariff, reservation.timezone)
                recorded = await claim.record_charge(
                    reservation=reservation,
                    tariff_id=tariff.tariff_id,
                    charged_window=window,
                    amount_cents=breakdown.total_cents,
                    currency=breakdown.currency,
                    now=self._clock.now(),
                )
                if recorded:
                    settled += 1
                else:
                    already_settled += 1

        logger.info(
            "settlement run complete",
            extra={
                "claimed": claimed,
                "settled": settled,
                "unpriced": unpriced,
                "already_settled": already_settled,
            },
        )
        return SettlementRunResult(
            claimed=claimed, settled=settled, unpriced=unpriced, already_settled=already_settled
        )
