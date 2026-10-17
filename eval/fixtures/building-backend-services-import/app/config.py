"""Environment configuration (sys layer). Cloud Run injects these as
container env vars; local dev sets them via .env / shell."""

from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class Settings:
    database_url: str
    gcp_project_id: str
    outbox_batch_size: int
    internal_endpoint_token: str


def load_settings() -> Settings:
    return Settings(
        database_url=os.environ["DATABASE_URL"],
        gcp_project_id=os.environ.get("GCP_PROJECT_ID", ""),
        outbox_batch_size=int(os.environ.get("OUTBOX_BATCH_SIZE", "100")),
        # Simple shared-secret check for /internal/outbox/publish in this
        # build. architecture-design.md's production intent is Cloud
        # Scheduler's OIDC-signed identity token, verified via Google's
        # auth library — swapping the check in app/api/internal_auth.py
        # for real OIDC verification doesn't touch anything else, but was
        # left as a token check here to avoid pulling in the extra
        # google-auth verification dependency/network call for what is,
        # for this exercise, a single internal endpoint.
        internal_endpoint_token=os.environ.get("INTERNAL_ENDPOINT_TOKEN", ""),
    )
