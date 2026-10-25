"""Synchronous retry and timing examples with preserved callable types."""

import logging
import math
import time
from collections.abc import Callable, Iterator
from contextlib import contextmanager
from functools import wraps
from typing import ParamSpec, TypeVar

P = ParamSpec("P")
R = TypeVar("R")
logger = logging.getLogger("ticketkit")


class TransientError(RuntimeError):
    """Only this explicitly retryable failure is retried by default."""


def retry(
    *,
    attempts: int = 3,
    base_delay: float = 0.01,
    max_delay: float = 1.0,
    retry_on: tuple[type[Exception], ...] = (TransientError,),
    sleep: Callable[[float], None] = time.sleep,
) -> Callable[[Callable[P, R]], Callable[P, R]]:
    if attempts < 1:
        raise ValueError("attempts must be at least 1")
    if not all(math.isfinite(x) and x >= 0 for x in (base_delay, max_delay)):
        raise ValueError("delays must be finite and non-negative")

    def decorate(func: Callable[P, R]) -> Callable[P, R]:
        @wraps(func)
        def wrapped(*args: P.args, **kwargs: P.kwargs) -> R:
            delay = min(base_delay, max_delay)
            for attempt in range(1, attempts + 1):
                try:
                    return func(*args, **kwargs)
                except retry_on:
                    if attempt == attempts:
                        raise
                    logger.warning("retry attempt=%d delay=%.3f", attempt, delay)
                    sleep(delay)
                    delay = min(delay * 2, max_delay)
            raise AssertionError("unreachable after validated attempts")

        return wrapped

    return decorate


@contextmanager
def timed_block(name: str) -> Iterator[None]:
    start = time.perf_counter()
    try:
        yield
    except Exception:
        logger.exception("block=%s failed", name)
        raise
    finally:
        logger.info("block=%s elapsed=%.6f", name, time.perf_counter() - start)


def timed(func: Callable[P, R]) -> Callable[P, R]:
    @wraps(func)
    def wrapped(*args: P.args, **kwargs: P.kwargs) -> R:
        with timed_block(func.__name__):
            return func(*args, **kwargs)

    return wrapped
