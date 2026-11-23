"""Applies the numbered files in migrations/ once each, in order (SD10).

Usage: DATABASE_URL=postgresql://... python -m parking_reservation.migrate [migrations-dir]
"""

import os
import sys
from pathlib import Path

import psycopg

_BOOKKEEPING = """
CREATE TABLE IF NOT EXISTS schema_migration (
    filename   text PRIMARY KEY,
    applied_at timestamptz NOT NULL DEFAULT now()
)
"""
_LOCK_KEY = (2, 1)


def migrate(database_url: str, directory: Path) -> list[str]:
    """Apply every pending file; return the names applied in this run."""
    applied_now: list[str] = []
    with psycopg.connect(database_url) as conn:
        conn.execute("SELECT pg_advisory_xact_lock(%s, %s)", _LOCK_KEY)
        conn.execute(_BOOKKEEPING)
        done = {row[0] for row in conn.execute("SELECT filename FROM schema_migration")}
        for path in sorted(directory.glob("*.sql")):
            if path.name in done:
                continue
            conn.execute(path.read_text())
            conn.execute("INSERT INTO schema_migration (filename) VALUES (%s)", (path.name,))
            applied_now.append(path.name)
    return applied_now


if __name__ == "__main__":
    url = os.environ.get("DATABASE_URL", "")
    if not url:
        sys.exit("usage: DATABASE_URL=postgresql://... python -m parking_reservation.migrate [dir]")
    folder = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("migrations")
    for name in migrate(url, folder):
        print(f"applied {name}")
