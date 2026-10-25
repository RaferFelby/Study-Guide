import asyncio

import pytest

from scheduler import (
    CircuitBreaker,
    RateLimitedError,
    Request,
    Scheduler,
    ToolSpec,
    merge_facts,
)


def test_parallel_concurrency_limit_and_request_order():
    async def scenario():
        active = 0
        peak = 0

        async def read(arguments):
            nonlocal active, peak
            active += 1
            peak = max(peak, active)
            await asyncio.sleep(0.01)
            active -= 1
            return {"value": arguments["value"]}

        requests = [Request(str(index), "read", {"value": index}) for index in range(5)]
        results = await Scheduler(
            {"read": ToolSpec(read, is_read_only=True)}, max_concurrency=2
        ).run_batch(requests)
        assert peak == 2
        assert [item["call_id"] for item in results] == [
            str(index) for index in range(5)
        ]
        assert all(item["ok"] for item in results)

    asyncio.run(scenario())


def test_serial_mode_has_peak_one():
    async def scenario():
        active = 0
        peak = 0

        async def read(arguments):
            nonlocal active, peak
            active += 1
            peak = max(peak, active)
            await asyncio.sleep(0)
            active -= 1
            return arguments

        requests = [Request(str(index), "read", {"value": index}) for index in range(3)]
        await Scheduler({"read": ToolSpec(read, is_read_only=True)}).run_batch(
            requests, parallel=False
        )
        assert peak == 1

    asyncio.run(scenario())


def test_same_safe_request_is_executed_once_per_batch():
    async def scenario():
        calls = 0

        async def read(arguments):
            nonlocal calls
            calls += 1
            return {"value": 1}

        requests = [Request("a", "read", {}), Request("b", "read", {})]
        results = await Scheduler(
            {"read": ToolSpec(read, is_read_only=True)}
        ).run_batch(requests)
        assert calls == 1
        assert [item["call_id"] for item in results] == ["a", "b"]
        results[0]["data"]["content"]["value"] = 100
        assert results[1]["data"]["content"]["value"] == 1

    asyncio.run(scenario())


def test_non_idempotent_writes_are_not_deduplicated():
    async def scenario():
        calls = 0

        async def write(arguments):
            nonlocal calls
            calls += 1
            return {"ticket": calls}

        requests = [Request("a", "write", {}), Request("b", "write", {})]
        await Scheduler({"write": ToolSpec(write, is_read_only=False)}).run_batch(
            requests
        )
        assert calls == 2

    asyncio.run(scenario())


def test_read_timeout_is_bounded_and_cancelled_between_attempts():
    async def scenario():
        calls = 0
        cleanups = 0

        async def slow(arguments):
            nonlocal calls, cleanups
            calls += 1
            try:
                await asyncio.sleep(10)
            finally:
                cleanups += 1

        scheduler = Scheduler(
            {"slow": ToolSpec(slow, is_read_only=True)},
            timeout_seconds=0.01,
            max_attempts=2,
            base_delay_seconds=0,
        )
        result = (await scheduler.run_batch([Request("a", "slow", {})]))[0]
        assert result["error"]["code"] == "timeout"
        assert calls == 2 and cleanups == 2

    asyncio.run(scenario())


def test_write_timeout_is_unknown_and_never_retried():
    async def scenario():
        calls = 0

        async def slow_write(arguments):
            nonlocal calls
            calls += 1
            await asyncio.sleep(10)

        scheduler = Scheduler(
            {"write": ToolSpec(slow_write, is_read_only=False)},
            timeout_seconds=0.01,
            max_attempts=5,
        )
        result = (await scheduler.run_batch([Request("a", "write", {})]))[0]
        assert result["error"]["code"] == "outcome_unknown"
        assert result["error"]["retryable"] is False
        assert calls == 1

    asyncio.run(scenario())


def test_rate_limit_retries_then_succeeds():
    async def scenario():
        calls = 0

        async def limited(arguments):
            nonlocal calls
            calls += 1
            if calls == 1:
                raise RateLimitedError(0.001)
            return {"ready": True}

        result = (
            await Scheduler(
                {"read": ToolSpec(limited, is_read_only=True)}, base_delay_seconds=0
            ).run_batch([Request("a", "read", {})])
        )[0]
        assert result["ok"] and result["attempts"] == 2

    asyncio.run(scenario())


def test_retry_after_beyond_budget_stops_instead_of_retrying_early():
    async def scenario():
        calls = 0

        async def limited(arguments):
            nonlocal calls
            calls += 1
            raise RateLimitedError(30)

        result = (
            await Scheduler(
                {"read": ToolSpec(limited, is_read_only=True)}, max_delay_seconds=0.1
            ).run_batch([Request("a", "read", {})])
        )[0]
        assert result["error"]["code"] == "rate_limited"
        assert calls == 1

    asyncio.run(scenario())


def test_circuit_opens_then_cooldown_allows_again():
    clock_value = [0.0]
    breaker = CircuitBreaker(
        failure_threshold=2, cooldown_seconds=5, clock=lambda: clock_value[0]
    )
    breaker.record_failure("read")
    assert breaker.allows("read")
    breaker.record_failure("read")
    assert not breaker.allows("read")
    clock_value[0] = 5.0
    assert breaker.allows("read")


def test_partial_failure_keeps_success_and_conflicts_are_not_silently_merged():
    async def scenario():
        async def read(arguments):
            return arguments

        requests = [
            Request("a", "read", {"field": "retention", "value": "14 days"}),
            Request("b", "read", {"field": "retention", "value": "30 days"}),
            Request("c", "missing", {}),
        ]
        results = await Scheduler(
            {"read": ToolSpec(read, is_read_only=True)}
        ).run_batch(requests)
        assert sum(item["ok"] for item in results) == 2
        combined = merge_facts(results)
        assert combined["conflicts"]
        assert "retention" not in combined["facts"]
        assert combined["failures"][0]["error"]["code"] == "unknown_tool"
        assert not combined["is_complete"]

    asyncio.run(scenario())


def test_long_result_has_valid_summary_and_full_result_reference():
    async def scenario():
        async def long(arguments):
            return {"text": "中文" * 100}

        scheduler = Scheduler(
            {"long": ToolSpec(long, is_read_only=True)}, max_output_characters=20
        )
        result = (await scheduler.run_batch([Request("a", "long", {})]))[0]
        assert result["ok"]
        summary = result["data"]
        assert summary["is_summary"] and summary["truncated"]
        assert len(summary["preview"]) == 20
        assert scheduler.read_full_result(summary["result_ref"])["text"] == "中文" * 100

    asyncio.run(scenario())


def test_parent_cancel_propagates_and_children_cleanup():
    async def scenario():
        entered = asyncio.Event()
        cleaned = asyncio.Event()

        async def blocking(arguments):
            entered.set()
            try:
                await asyncio.sleep(10)
            finally:
                cleaned.set()

        scheduler = Scheduler(
            {"read": ToolSpec(blocking, is_read_only=True)}, timeout_seconds=20
        )
        task = asyncio.create_task(scheduler.run_batch([Request("a", "read", {})]))
        await entered.wait()
        task.cancel()
        with pytest.raises(asyncio.CancelledError):
            await task
        assert cleaned.is_set()

    asyncio.run(scenario())


def test_batch_size_is_rejected_before_any_execution():
    async def scenario():
        calls = 0

        async def read(arguments):
            nonlocal calls
            calls += 1
            return {}

        scheduler = Scheduler({"read": ToolSpec(read, is_read_only=True)}, max_calls=1)
        with pytest.raises(ValueError):
            await scheduler.run_batch(
                [Request("a", "read", {}), Request("b", "read", {})]
            )
        assert calls == 0

    asyncio.run(scenario())


def test_dependency_is_executed_as_two_stages():
    async def scenario():
        async def get_order(arguments):
            return {"order_id": "ORDER-1"}

        async def get_status(arguments):
            assert arguments["order_id"] == "ORDER-1"
            return {"status": "open"}

        scheduler = Scheduler(
            {
                "order": ToolSpec(get_order, is_read_only=True),
                "status": ToolSpec(get_status, is_read_only=True),
            }
        )
        first = (await scheduler.run_batch([Request("a", "order", {})]))[0]
        order_id = first["data"]["content"]["order_id"]
        second = (
            await scheduler.run_batch([Request("b", "status", {"order_id": order_id})])
        )[0]
        assert second["ok"]

    asyncio.run(scenario())
