"""No-network demo: bounded concurrency, per-tool timeout and cancellation."""

import asyncio
import logging

from .observability import request_scope

logger = logging.getLogger("ticketkit")


async def simulated_tool(name: str, delay: float) -> str:
    await asyncio.sleep(delay)
    return f"{name}:ok"


async def run_parallel(
    jobs: list[tuple[str, float]], *, concurrency: int = 2, timeout: float = 0.03
) -> list[str]:
    if concurrency < 1 or timeout <= 0:
        raise ValueError("concurrency and timeout must be positive")
    if any(delay < 0 for _, delay in jobs):
        raise ValueError("job delays must be non-negative")
    semaphore = asyncio.Semaphore(concurrency)

    async def one(name: str, delay: float) -> str:
        with request_scope(name):
            async with semaphore:
                try:
                    result = await asyncio.wait_for(
                        simulated_tool(name, delay), timeout
                    )
                except TimeoutError:
                    logger.warning("tool timeout")
                    return f"{name}:timeout"
                logger.info("tool completed")
                return result

    results = await asyncio.gather(*(one(name, delay) for name, delay in jobs))
    return list(results)
