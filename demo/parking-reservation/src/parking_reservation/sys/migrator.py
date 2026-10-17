from importlib import resources

import psycopg
from psycopg.rows import dict_row

from parking_reservation.repo.sql_loader import load_sql

_LOCK_KEY = 7_203_011  # advisory lock so two deploys cannot migrate at once
_LOCK = load_sql("parking_reservation.sys", "migration_lock")
_UNLOCK = load_sql("parking_reservation.sys", "migration_unlock")
_TABLE_EXISTS = load_sql("parking_reservation.sys", "migration_table_exists")
_APPLIED = load_sql("parking_reservation.sys", "migration_applied")
_RECORD = load_sql("parking_reservation.sys", "migration_record")


def migrate(database_url: str) -> list[str]:
    """Applies migration files not yet recorded in schema_migration, in file-name order.

    Each file runs in its own transaction together with its bookkeeping row.
    Returns the names applied by this call.
    """
    files = sorted(
        (f for f in resources.files("parking_reservation.migrations").iterdir() if f.name.endswith(".sql")),
        key=lambda f: f.name,
    )
    applied: list[str] = []
    with psycopg.connect(database_url, autocommit=True, row_factory=dict_row) as conn:
        conn.execute(_LOCK, {"key": _LOCK_KEY})
        try:
            done = _already_applied(conn)
            for f in files:
                if f.name in done:
                    continue
                with conn.transaction():
                    conn.execute(f.read_text("utf-8"))
                    conn.execute(_RECORD, {"version": f.name})
                applied.append(f.name)
        finally:
            conn.execute(_UNLOCK, {"key": _LOCK_KEY})
    return applied


def _already_applied(conn: psycopg.Connection[dict[str, object]]) -> set[str]:
    exists = conn.execute(_TABLE_EXISTS).fetchone()
    if exists is None or not exists["present"]:
        return set()
    return {str(row["version"]) for row in conn.execute(_APPLIED)}
