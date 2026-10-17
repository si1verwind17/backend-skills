"""Loads raw SQL from app/repo/sql/*.sql (backend-code-conventions: "SQL as
raw strings belongs in .sql files the code loads")."""

from __future__ import annotations

from functools import cache
from pathlib import Path

_SQL_DIR = Path(__file__).parent / "sql"


@cache
def load_sql(name: str) -> str:
    """name is the file stem, e.g. load_sql('insert_reservation')."""
    return (_SQL_DIR / f"{name}.sql").read_text()
