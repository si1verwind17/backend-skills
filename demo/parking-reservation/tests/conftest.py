"""Fixtures: a real Postgres in a container on a host port in 55432-55499 (SD5)."""

import os
import socket
import subprocess
import time
from collections.abc import Iterator
from pathlib import Path
from uuid import uuid4

import psycopg
import pytest

from parking_reservation.migrate import migrate
from parking_reservation.repo.database import Pool, create_pool

IMAGE = "postgres:17.11"
PORTS = range(55432, 55500)
MIGRATIONS = Path(__file__).resolve().parent.parent / "migrations"


def _free_port() -> int:
    for port in PORTS:
        with socket.socket() as probe:
            if probe.connect_ex(("127.0.0.1", port)) != 0:
                return port
    raise RuntimeError("no free host port in 55432-55499")


@pytest.fixture(scope="session")
def database_url() -> Iterator[str]:
    port = _free_port()
    name = f"parking-it-{os.getpid()}-{uuid4().hex[:6]}"
    subprocess.run(
        [
            "docker",
            "run",
            "-d",
            "--rm",
            "--name",
            name,
            "-e",
            "POSTGRES_PASSWORD=test",
            "-p",
            f"127.0.0.1:{port}:5432",
            IMAGE,
        ],
        check=True,
        capture_output=True,
    )
    url = f"postgresql://postgres:test@127.0.0.1:{port}/postgres"
    try:
        deadline = time.monotonic() + 60
        while True:
            try:
                with psycopg.connect(url, connect_timeout=2):
                    break
            except psycopg.OperationalError:
                if time.monotonic() > deadline:
                    raise
                time.sleep(0.5)
        migrate(url, MIGRATIONS)
        yield url
    finally:
        subprocess.run(["docker", "rm", "-f", name], capture_output=True)


@pytest.fixture
def pool(database_url: str) -> Iterator[Pool]:
    with psycopg.connect(database_url, autocommit=True) as conn:
        conn.execute("TRUNCATE outbox, reservation, spot, garage RESTART IDENTITY CASCADE")
    created = create_pool(database_url)
    created.open(wait=True)
    yield created
    created.close()


@pytest.fixture
def seed_garage(pool: Pool):  # type: ignore[no-untyped-def]
    """Insert a garage with `spots` active spots and return its id."""

    def seed(spots: int, timezone: str = "UTC", name: str = "G") -> int:
        with pool.connection() as conn:
            garage = conn.execute(
                "INSERT INTO garage (name, timezone, updated_at) VALUES (%s, %s, now()) "
                "RETURNING garage_id",
                (name, timezone),
            ).fetchone()
            assert garage is not None
            for n in range(spots):
                conn.execute(
                    "INSERT INTO spot (garage_id, label, updated_at) VALUES (%s, %s, now())",
                    (garage["garage_id"], f"S{n + 1}"),
                )
            return int(garage["garage_id"])

    return seed
