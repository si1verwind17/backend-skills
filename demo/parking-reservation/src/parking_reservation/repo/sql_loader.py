from importlib import resources


def load_sql(package: str, name: str) -> str:
    """Reads one query from <package>/sql/<name>.sql; callers read it once at import."""
    return resources.files(package).joinpath("sql", f"{name}.sql").read_text("utf-8")
