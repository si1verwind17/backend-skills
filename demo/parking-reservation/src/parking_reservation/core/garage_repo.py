from typing import Protocol


class GarageRepo(Protocol):
    def find_time_zone(self, garage_code: str) -> str | None: ...
