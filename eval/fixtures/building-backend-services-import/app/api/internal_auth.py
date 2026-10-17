"""Guards the internal /internal/outbox/publish endpoint. See
app/config.py for why this is a shared-secret token check rather than
full Cloud Scheduler OIDC verification in this build."""

from __future__ import annotations

from fastapi import Header, HTTPException, Request, status


async def require_internal_caller(
    request: Request, x_internal_token: str = Header(default="")
) -> None:
    expected = request.app.state.settings.internal_endpoint_token
    if not expected or x_internal_token != expected:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="forbidden")
