from pydantic import AwareDatetime, BaseModel, ConfigDict, Field


class CreateReservationRequest(BaseModel):
    """Wire shape of POST /v1/reservations; shape checks only, business rules are in core."""

    model_config = ConfigDict(extra="forbid")

    garage_code: str = Field(min_length=1, max_length=64, pattern=r"^[^\x00-\x1f\x7f]+$")
    start_at: AwareDatetime
    end_at: AwareDatetime
