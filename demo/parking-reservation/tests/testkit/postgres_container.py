import os
import subprocess
import time

import psycopg

IMAGE = "postgres:18.6"  # same minor as Cloud SQL today (stack selection, SD5)
NAME = "parking-reservation-test-pg"
PORT = int(os.environ.get("TEST_DB_PORT", "55432"))  # host ports 55432-55499 (OI-28)
PASSWORD = "test"


def database_url(dbname: str = "postgres") -> str:
    return f"postgresql://postgres:{PASSWORD}@127.0.0.1:{PORT}/{dbname}"


def _docker(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(["docker", *args], capture_output=True, text=True, check=False)


def ensure_running() -> bool:
    """Starts the test database unless it already runs; returns True when this call started it."""
    state = _docker("inspect", "-f", "{{.State.Running}}", NAME)
    if state.returncode == 0 and state.stdout.strip() == "true":
        return False
    _docker("rm", "-f", NAME)
    started = _docker(
        "run", "-d", "--name", NAME, "-e", f"POSTGRES_PASSWORD={PASSWORD}", "-p", f"{PORT}:5432", IMAGE
    )
    if started.returncode != 0:
        raise RuntimeError(f"cannot start {IMAGE}: {started.stderr}")
    _wait_until_ready()
    return True


def stop() -> None:
    _docker("rm", "-f", NAME)


def _wait_until_ready() -> None:
    deadline = time.monotonic() + 60
    while time.monotonic() < deadline:
        try:
            with psycopg.connect(database_url(), connect_timeout=2) as conn:
                conn.execute("SELECT 1")
            return
        except psycopg.OperationalError:
            time.sleep(0.5)
    raise RuntimeError("test database did not become ready")
