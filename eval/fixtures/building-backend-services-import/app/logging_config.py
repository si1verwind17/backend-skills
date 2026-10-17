"""Minimal logging setup. Cloud Run captures stdout; a plain formatter is
enough for this small service (structured/JSON logging would be the next
step if log-based alerting on billing_outbox.last_error, per
architecture-design.md, needs field-level queries)."""

from __future__ import annotations

import logging


def configure_logging(level: int = logging.INFO) -> None:
    logging.basicConfig(
        level=level,
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )
