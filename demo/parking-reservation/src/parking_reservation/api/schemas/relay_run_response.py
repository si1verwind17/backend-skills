from pydantic import BaseModel


class RelayRunResponse(BaseModel):
    published: int
    failed: int
    parked: int
    oldest_pending_age_seconds: float | None
