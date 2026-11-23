"""Loads the repository's SQL from the .sql files beside it."""

from functools import cache
from importlib import resources
from typing import LiteralString


@cache
def load(name: str) -> LiteralString:
    """Return the text of repo/sql/<name>.sql. The files are code we ship, not user input."""
    text = resources.files("parking_reservation.repo").joinpath("sql", f"{name}.sql").read_text()
    return text
