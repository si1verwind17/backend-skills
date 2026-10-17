import psycopg
import pytest

from parking_reservation.sys.migrator import migrate

pytestmark = pytest.mark.integration


def test_second_run_applies_nothing(database_url: str) -> None:
    assert migrate(database_url) == []


def test_every_table_and_column_has_a_description_and_created_at(database_url: str) -> None:
    with psycopg.connect(database_url) as conn:
        undescribed = conn.execute(
            """SELECT c.relname, a.attname FROM pg_class c
               JOIN pg_attribute a ON a.attrelid = c.oid AND a.attnum > 0 AND NOT a.attisdropped
               LEFT JOIN pg_description d ON d.objoid = c.oid AND d.objsubid = a.attnum
               WHERE c.relnamespace = 'public'::regnamespace AND c.relkind = 'r' AND d.description IS NULL"""
        ).fetchall()
        tables = [
            r[0]
            for r in conn.execute(
                "SELECT relname FROM pg_class WHERE relnamespace = 'public'::regnamespace AND relkind = 'r'"
            )
        ]
        without_created_at = [
            t
            for t in tables
            if not conn.execute(
                "SELECT 1 FROM information_schema.columns "
                "WHERE table_name = %s AND column_name = 'created_at'",
                (t,),
            ).fetchone()
        ]
    assert undescribed == []
    assert without_created_at == []


def test_pool_connections_are_read_committed_and_utc_whatever_the_server_default(database_url: str) -> None:
    from parking_reservation.sys.database import open_pool

    with psycopg.connect(database_url, autocommit=True) as admin:
        admin.execute("ALTER DATABASE postgres SET default_transaction_isolation = 'serializable'")
        admin.execute("ALTER DATABASE postgres SET TimeZone = 'Asia/Tokyo'")
    pool = open_pool(database_url)
    try:
        with pool.connection() as conn:
            row = conn.execute(
                "SELECT current_setting('transaction_isolation') AS iso, current_setting('TimeZone') AS tz"
            ).fetchone()
    finally:
        pool.close()
        with psycopg.connect(database_url, autocommit=True) as admin:
            admin.execute("ALTER DATABASE postgres RESET default_transaction_isolation")
            admin.execute("ALTER DATABASE postgres RESET TimeZone")
    assert row == {"iso": "read committed", "tz": "UTC"}
