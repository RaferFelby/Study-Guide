"""Run with python -m ticketkit after installing the local package."""

import asyncio
import json
from pathlib import Path

from .async_tools import run_parallel
from .config import Config
from .data import generated_tickets, summarize
from .observability import close_logging, request_scope, setup_logging
from .resilience import TransientError, retry, timed


def main() -> None:
    config = Config.from_env()
    logger = setup_logging(Path("logs/demo.log"))
    try:
        with request_scope("demo-001"):
            counter = 0

            @timed
            @retry(attempts=config.attempts)
            def load_summary() -> dict[str, int]:
                nonlocal counter
                counter += 1
                if counter == 1:
                    raise TransientError("simulated temporary unavailability")
                return summarize(generated_tickets(100_000))

            totals = load_summary()
            logger.info("processed rows=%d attempts=%d", sum(totals.values()), counter)
            print(json.dumps(totals, ensure_ascii=False))
        # Timeout behavior is demonstrated deterministically in the tests as well.
        results = asyncio.run(run_parallel([("fast", 0.0), ("slow", 1.0)]))
        print(json.dumps(results, ensure_ascii=False))
    finally:
        close_logging()


if __name__ == "__main__":
    main()
