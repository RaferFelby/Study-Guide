"""A package-owned logger with per-request context and rotating files."""

import logging
from collections.abc import Iterator
from contextlib import contextmanager
from contextvars import ContextVar
from logging.handlers import RotatingFileHandler
from pathlib import Path

request_id: ContextVar[str] = ContextVar("ticketkit_request_id", default="-")


class RequestFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        record.request_id = request_id.get()
        return True


@contextmanager
def request_scope(value: str) -> Iterator[None]:
    token = request_id.set(value)
    try:
        yield
    finally:
        request_id.reset(token)


def setup_logging(path: Path, max_bytes: int = 100_000) -> logging.Logger:
    """Call at startup, before concurrent tasks begin."""
    path.parent.mkdir(parents=True, exist_ok=True)
    logger = logging.getLogger("ticketkit")
    logger.setLevel(logging.INFO)
    logger.propagate = False
    # This function owns only the ticketkit logger, not the application's root.
    for handler in logger.handlers[:]:
        logger.removeHandler(handler)
        handler.close()
    formatter = logging.Formatter(
        "%(asctime)s %(levelname)s request_id=%(request_id)s %(message)s"
    )
    handlers: list[logging.Handler] = [
        logging.StreamHandler(),
        RotatingFileHandler(path, maxBytes=max_bytes, backupCount=2, encoding="utf-8"),
    ]
    for handler in handlers:
        handler.setFormatter(formatter)
        handler.addFilter(RequestFilter())
        logger.addHandler(handler)
    return logger


def close_logging() -> None:
    logger = logging.getLogger("ticketkit")
    for handler in logger.handlers[:]:
        logger.removeHandler(handler)
        handler.close()
