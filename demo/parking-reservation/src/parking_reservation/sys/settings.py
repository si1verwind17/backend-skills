from collections.abc import Mapping
from dataclasses import dataclass

from parking_reservation.sys.config_error import ConfigError


@dataclass(frozen=True)
class Settings:
    database_url: str
    identity_header: str
    gcp_project: str
    scheduler_service_account: str
    relay_audience: str


def load_settings(env: Mapping[str, str]) -> Settings:
    return Settings(
        database_url=required_env(env, "DATABASE_URL"),
        identity_header=required_env(env, "IDENTITY_HEADER"),
        gcp_project=required_env(env, "GCP_PROJECT"),
        scheduler_service_account=required_env(env, "SCHEDULER_SERVICE_ACCOUNT"),
        relay_audience=required_env(env, "RELAY_AUDIENCE"),
    )


def required_env(env: Mapping[str, str], name: str) -> str:
    value = env.get(name, "").strip()
    if not value:
        raise ConfigError(f"{name} is required and must not be empty")
    return value
