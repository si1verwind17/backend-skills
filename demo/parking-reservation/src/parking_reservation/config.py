"""Service configuration, read once at startup and validated before anything is built."""

import re
from collections.abc import Mapping
from dataclasses import dataclass, field

from psycopg import ProgrammingError
from psycopg.conninfo import conninfo_to_dict

_REQUIRED = (
    "DATABASE_URL",
    "GCP_PROJECT",
    "AUTH_AUDIENCE",
    "FRONT_END_SERVICE_ACCOUNT",
    "SCHEDULER_SERVICE_ACCOUNT",
)


_PROJECT_ID = re.compile(r"^[a-z][a-z0-9-]{4,28}[a-z0-9]$")


class ConfigError(Exception):
    """The deployment is misconfigured. Messages name settings, never their values."""


@dataclass(frozen=True)
class Settings:
    database_url: str = field(repr=False)
    gcp_project: str
    auth_audience: str
    front_end_service_account: str
    scheduler_service_account: str


def load_settings(env: Mapping[str, str]) -> Settings:
    """Build Settings from the environment or raise ConfigError naming what is wrong."""
    missing = [name for name in _REQUIRED if not env.get(name, "").strip()]
    if missing:
        raise ConfigError(f"missing or empty settings: {', '.join(missing)}")
    database_url = env["DATABASE_URL"].strip()
    if not database_url.startswith(("postgresql://", "postgres://")):
        raise ConfigError("DATABASE_URL must be a postgresql:// connection string")
    if not _PROJECT_ID.fullmatch(env["GCP_PROJECT"].strip()):
        raise ConfigError("GCP_PROJECT is not a valid project id")
    try:
        conninfo_to_dict(database_url)
    except ProgrammingError:
        raise ConfigError("DATABASE_URL is not a valid connection string") from None
    return Settings(
        database_url=database_url,
        gcp_project=env["GCP_PROJECT"].strip(),
        auth_audience=env["AUTH_AUDIENCE"].strip(),
        front_end_service_account=env["FRONT_END_SERVICE_ACCOUNT"].strip(),
        scheduler_service_account=env["SCHEDULER_SERVICE_ACCOUNT"].strip(),
    )
