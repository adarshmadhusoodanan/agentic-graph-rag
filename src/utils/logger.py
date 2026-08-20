"""Structured logging setup.

One place configures how the whole application logs, so every module gets
consistent, environment-appropriate output instead of ad-hoc print() calls
or per-module logging.basicConfig() calls that fight each other.

Usage, from any module:

    from src.utils.logger import get_logger

    logger = get_logger(__name__)
    logger.info("Ingested %d chunks", count)
"""

import json
import logging
import sys
from datetime import datetime, timezone

from src.config import EnvironmentOption, settings


class JSONFormatter(logging.Formatter):
    """Render each log record as one JSON line.

    Used outside local development so logs are directly ingestible by log
    aggregators (CloudWatch, Datadog, etc.) without a separate parser --
    the same reason CloudWatch Logs Insights queries are painless when the
    source is already structured.
    """

    def format(self, record: logging.LogRecord) -> str:
        payload = {
            "timestamp": datetime.fromtimestamp(
                record.created, tz=timezone.utc
            ).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)
        return json.dumps(payload)


_configured = False


def _configure_root_logger() -> None:
    """Attach exactly one handler to the root logger, once per process."""
    global _configured
    if _configured:
        return

    handler = logging.StreamHandler(sys.stdout)
    if settings.ENV == EnvironmentOption.DEVELOPMENT:
        handler.setFormatter(
            logging.Formatter(
                fmt="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
                datefmt="%Y-%m-%d %H:%M:%S",
            )
        )
    else:
        # staging / production: structured JSON for log aggregators
        handler.setFormatter(JSONFormatter())

    root = logging.getLogger()
    root.setLevel(settings.LOG_LEVEL)
    root.addHandler(handler)
    _configured = True


def get_logger(name: str) -> logging.Logger:
    """Return a configured logger for `name` (pass __name__ from the caller)."""
    _configure_root_logger()
    return logging.getLogger(name)
