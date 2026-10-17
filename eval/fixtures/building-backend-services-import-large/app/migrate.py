"""Applies migrations/NNNN_*.sql in order, each once, recording what has
run in schema_migrations. Run as `python -m app.migrate` (locally, and as
the Cloud Run job step in cloudbuild.yaml before the new revision takes
traffic).

Each file runs in its own transaction together with its bookkeeping row,
so a failing migration leaves neither half-applied schema nor a record
claiming it ran. A session-level advisory lock keeps two concurrent runs
from applying the same file twice.
"""

from __future__ import annotations

import logging
import os
import re
import sys
from pathlib import Path

import psycopg

from app.logging_config import configure_logging

logger = logging.getLogger(__name__)

MIGRATIONS_DIR = Path(__file__).resolve().parents[1] / "migrations"
_MIGRATION_FILE = re.compile(r"^(\d{4})_[a-z0-9_]+\.sql$")
_LOCK_KEY = 7_302_114  # arbitrary, fixed: identifies "schema migration" locks

_CREATE_LEDGER = """
CREATE TABLE IF NOT EXISTS schema_migrations (
    version     text PRIMARY KEY,
    filename    text NOT NULL,
    applied_at  timestamptz NOT NULL DEFAULT now()
)
"""


def discover(directory: Path = MIGRATIONS_DIR) -> list[tuple[str, Path]]:
    """(version, path) pairs sorted by version. Refuses duplicate
    versions and files that do not follow the NNNN_name.sql pattern, so a
    typo cannot silently skip a migration."""
    found: dict[str, Path] = {}
    for path in sorted(directory.glob("*.sql")):
        match = _MIGRATION_FILE.fullmatch(path.name)
        if match is None:
            raise SystemExit(f"migration file {path.name} does not match NNNN_name.sql")
        version = match.group(1)
        if version in found:
            raise SystemExit(f"duplicate migration version {version}: {found[version].name}, {path.name}")
        found[version] = path
    return sorted(found.items())


def pending(applied: set[str], available: list[tuple[str, Path]]) -> list[tuple[str, Path]]:
    return [(version, path) for version, path in available if version not in applied]


def migrate(dsn: str, directory: Path = MIGRATIONS_DIR) -> list[str]:
    """Applies pending migrations; returns the versions applied."""
    available = discover(directory)
    applied_now: list[str] = []
    with psycopg.connect(dsn, autocommit=True) as conn:
        conn.execute("SELECT pg_advisory_lock(%s)", (_LOCK_KEY,))
        try:
            conn.execute(_CREATE_LEDGER)
            applied = {row[0] for row in conn.execute("SELECT version FROM schema_migrations")}
            for version, path in pending(applied, available):
                logger.info("applying migration", extra={"version": version, "file": path.name})
                with conn.transaction():
                    conn.execute(path.read_text())
                    conn.execute(
                        "INSERT INTO schema_migrations (version, filename) VALUES (%s, %s)",
                        (version, path.name),
                    )
                applied_now.append(version)
        finally:
            conn.execute("SELECT pg_advisory_unlock(%s)", (_LOCK_KEY,))
    return applied_now


def main() -> int:
    configure_logging()
    applied = migrate(os.environ["DATABASE_URL"])
    if applied:
        logger.info("migrations applied: %s", ", ".join(applied))
    else:
        logger.info("schema is up to date")
    return 0


if __name__ == "__main__":
    sys.exit(main())
