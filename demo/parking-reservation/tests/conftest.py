import logging
from collections.abc import Iterator

import pytest

from parking_reservation.sys.migrator import migrate
from testkit import postgres_container
from testkit.seed import reset_and_seed


@pytest.fixture(scope="session")
def database_url() -> Iterator[str]:
    """One migrated Postgres 18.6 for the session; torn down only if this session started it."""
    started = postgres_container.ensure_running()
    url = postgres_container.database_url()
    import psycopg

    with psycopg.connect(url, autocommit=True) as conn:
        conn.execute("DROP SCHEMA public CASCADE")
        conn.execute("CREATE SCHEMA public")
    migrate(url)
    yield url
    if started:
        postgres_container.stop()


@pytest.fixture
def seeded(database_url: str) -> str:
    reset_and_seed(database_url, {"G1": ("UTC", ["A1", "A2"]), "G2": ("Europe/Zurich", ["B1"])})
    return database_url


@pytest.fixture
def restore_root_logging() -> Iterator[None]:
    """Entry points install the JSON handler on the root logger; put the test runner's handlers back."""
    root = logging.getLogger()
    saved, level = root.handlers[:], root.level
    yield
    root.handlers[:], root.level = saved, level
