"""Structured JSON logging with correlation ID support."""

import json
import logging
import sys
import uuid
from contextlib import contextmanager
from contextvars import ContextVar
from datetime import datetime, timezone

# Correlation ID context variable for request tracing
_correlation_id: ContextVar[str | None] = ContextVar("correlation_id", default=None)


def get_correlation_id() -> str | None:
    """Get the current correlation ID from context."""
    return _correlation_id.get()


def set_correlation_id(correlation_id: str | None = None) -> str:
    """Set a correlation ID in context. Generates one if not provided."""
    cid = correlation_id or uuid.uuid4().hex[:16]
    _correlation_id.set(cid)
    return cid


@contextmanager
def correlation_id_ctx(correlation_id: str | None = None):
    """Context manager that sets a correlation ID and resets it on exit."""
    token = _correlation_id.set(correlation_id or uuid.uuid4().hex[:16])
    try:
        yield _correlation_id.get()
    finally:
        _correlation_id.reset(token)


class JSONFormatter(logging.Formatter):
    """Formats log records as structured JSON lines."""

    def format(self, record: logging.LogRecord) -> str:
        log_entry: dict = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "module": record.name,
            "message": record.getMessage(),
        }

        # Add correlation ID if present
        cid = _correlation_id.get()
        if cid is not None:
            log_entry["correlation_id"] = cid

        # Add extra context fields (anything passed via `extra={}` on log calls)
        for key, value in record.__dict__.items():
            if key not in (
                "name",
                "msg",
                "args",
                "created",
                "relativeCreated",
                "exc_info",
                "exc_text",
                "stack_info",
                "lineno",
                "funcName",
                "pathname",
                "filename",
                "module",
                "levelno",
                "levelname",
                "msecs",
                "thread",
                "threadName",
                "taskName",
                "processName",
                "process",
                "message",
            ):
                log_entry[key] = value

        # Add exception info if present
        if record.exc_info and record.exc_info[1] is not None:
            log_entry["exception"] = self.formatException(record.exc_info)

        return json.dumps(log_entry, default=str)


def get_logger(name: str) -> logging.Logger:
    """Return a configured logger with JSON formatting on stdout.

    Args:
        name: Logger name, typically the module path (e.g. ``src.ml.inference``).
    """
    logger = logging.getLogger(name)

    # Avoid adding duplicate handlers if called multiple times
    if not logger.handlers:
        handler = logging.StreamHandler(sys.stdout)
        handler.setFormatter(JSONFormatter())
        logger.addHandler(handler)

    # Import settings lazily to avoid circular imports at module load time
    try:
        from src.config.settings import get_settings

        logger.setLevel(getattr(logging, get_settings().LOG_LEVEL.upper(), logging.INFO))
    except Exception:
        logger.setLevel(logging.INFO)

    logger.propagate = False
    return logger
