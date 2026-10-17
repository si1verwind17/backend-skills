import logging
import os
import sys

from parking_reservation.sys.config_error import ConfigError
from parking_reservation.sys.logging_setup import configure_logging
from parking_reservation.sys.migrator import migrate
from parking_reservation.sys.settings import required_env

_log = logging.getLogger("parking_reservation.migrate")


def main() -> int:
    """Entry point of the migration job: `python -m parking_reservation.migrate_main`.

    Exit codes: 0 applied (or nothing to do), 2 bad configuration, 1 a migration failed.
    """
    configure_logging()
    try:
        database_url = required_env(os.environ, "DATABASE_URL")
    except ConfigError as error:
        _log.error("migration configuration invalid", extra={"fields": {"reason": str(error)}})
        return 2
    try:
        applied = migrate(database_url)
    except Exception:
        _log.error("migration failed", exc_info=True)
        return 1
    _log.info("migrations applied", extra={"fields": {"applied": applied}})
    return 0


if __name__ == "__main__":
    sys.exit(main())
