import pytest

from parking_reservation.sys.config_error import ConfigError
from parking_reservation.sys.settings import load_settings

GOOD = {
    "DATABASE_URL": "postgresql://x",
    "IDENTITY_HEADER": "x-claims",
    "GCP_PROJECT": "proj",
    "SCHEDULER_SERVICE_ACCOUNT": "s@proj.iam.gserviceaccount.com",
    "RELAY_AUDIENCE": "https://svc",
}


def test_loads_a_complete_environment() -> None:
    assert load_settings(GOOD).identity_header == "x-claims"


@pytest.mark.parametrize("name", sorted(GOOD))
@pytest.mark.parametrize("bad", [None, "", "   "])
def test_missing_or_blank_values_are_a_config_error(name: str, bad: str | None) -> None:
    env = {k: v for k, v in GOOD.items() if k != name}
    if bad is not None:
        env[name] = bad
    with pytest.raises(ConfigError):
        load_settings(env)
