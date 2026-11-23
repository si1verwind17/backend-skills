from pathlib import Path

import psycopg

from parking_reservation.migrate import migrate
from tests.conftest import MIGRATIONS


def test_migrations_are_recorded_and_not_reapplied(database_url: str) -> None:
    assert migrate(database_url, MIGRATIONS) == []
    expected = sorted(p.name for p in Path(MIGRATIONS).glob("*.sql"))
    with psycopg.connect(database_url) as conn:
        names = [r[0] for r in conn.execute("SELECT filename FROM schema_migration ORDER BY 1")]
    assert names == expected


def test_every_table_and_column_has_a_comment(database_url: str) -> None:
    with psycopg.connect(database_url) as conn:
        missing = conn.execute(
            """
            SELECT c.relname, a.attname
            FROM pg_class c JOIN pg_namespace n ON n.oid = c.relnamespace
            JOIN pg_attribute a ON a.attrelid = c.oid AND a.attnum > 0 AND NOT a.attisdropped
            WHERE n.nspname = 'public' AND c.relkind = 'r' AND c.relname <> 'schema_migration'
              AND col_description(c.oid, a.attnum) IS NULL
            """
        ).fetchall()
        tables = conn.execute(
            """
            SELECT c.relname FROM pg_class c JOIN pg_namespace n ON n.oid = c.relnamespace
            WHERE n.nspname = 'public' AND c.relkind = 'r' AND c.relname <> 'schema_migration'
              AND obj_description(c.oid, 'pg_class') IS NULL
            """
        ).fetchall()
    assert missing == [] and tables == []
