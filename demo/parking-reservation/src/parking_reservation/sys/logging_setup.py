import json
import logging
import sys
from typing import Any


class JsonFormatter(logging.Formatter):
    """One JSON object per line, the shape Cloud Logging parses (severity, message, fields)."""

    def format(self, record: logging.LogRecord) -> str:
        entry: dict[str, Any] = {"severity": record.levelname, "message": record.getMessage()}
        entry.update(getattr(record, "fields", {}))
        if record.exc_info:
            entry["exception"] = self.formatException(record.exc_info)
        return json.dumps(entry, default=str)


def configure_logging() -> None:
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(JsonFormatter())
    root = logging.getLogger()
    root.handlers[:] = [handler]
    root.setLevel(logging.INFO)
