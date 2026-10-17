from datetime import UTC, datetime

import psycopg

SEED_TIME = datetime(2026, 1, 1, tzinfo=UTC)


def reset_and_seed(database_url: str, garages: dict[str, tuple[str, list[str]]]) -> None:
    """Empties the data tables and inserts garages: code -> (time zone, spot labels)."""
    with psycopg.connect(database_url, autocommit=True) as conn:
        conn.execute("TRUNCATE outbox_event, reservation, spot, garage RESTART IDENTITY CASCADE")
        for code, (zone, labels) in garages.items():
            row = conn.execute(
                "INSERT INTO garage (code, name, time_zone, updated_at) "
                "VALUES (%s, %s, %s, %s) RETURNING garage_id",
                (code, f"Garage {code}", zone, SEED_TIME),
            ).fetchone()
            assert row is not None
            for label in labels:
                conn.execute(
                    "INSERT INTO spot (garage_id, label, updated_at) VALUES (%s, %s, %s)",
                    (row[0], label, SEED_TIME),
                )
