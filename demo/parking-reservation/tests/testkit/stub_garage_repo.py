class StubGarageRepo:
    def __init__(self, zones: dict[str, str]) -> None:
        self._zones = zones

    def find_time_zone(self, garage_code: str) -> str | None:
        return self._zones.get(garage_code)
