"""Measure Python allocations; values are environment-specific, not RSS."""

import gc
import json
import time
import tracemalloc
from collections.abc import Callable
from functools import partial

from .data import generated_tickets, summarize


def measure(action: Callable[[], dict[str, int]]) -> dict[str, object]:
    gc.collect()
    tracemalloc.start()
    start = time.perf_counter()
    try:
        totals = action()
        elapsed = time.perf_counter() - start
        _, peak = tracemalloc.get_traced_memory()
    finally:
        tracemalloc.stop()
    return {"totals": totals, "peak_python_bytes": peak, "elapsed_seconds": elapsed}


def stream_summary(count: int) -> dict[str, int]:
    return summarize(generated_tickets(count))


def list_summary(count: int) -> dict[str, int]:
    return summarize(list(generated_tickets(count)))


def main() -> None:
    report: dict[str, object] = {}
    for count in (10_000, 100_000):
        report[f"stream_{count}"] = measure(partial(stream_summary, count))
        report[f"list_{count}"] = measure(partial(list_summary, count))
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
