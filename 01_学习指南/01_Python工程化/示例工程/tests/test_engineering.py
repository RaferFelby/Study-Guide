import asyncio
import io
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from ticketkit import (
    Config,
    TransientError,
    generated_tickets,
    read_tickets,
    retry,
    timed,
)
from ticketkit.async_tools import run_parallel
from ticketkit.config import ConfigError
from ticketkit.data import DataError, parse_ticket, summarize
from ticketkit.observability import (
    close_logging,
    request_id,
    request_scope,
    setup_logging,
)
from ticketkit.resilience import timed_block


class RetryTests(unittest.TestCase):
    def test_success_backoff_and_metadata(self):
        waits = []
        calls = 0

        @retry(attempts=4, base_delay=0.1, max_delay=0.15, sleep=waits.append)
        def work(x: int, *, offset: int = 1) -> int:
            """Example metadata."""
            nonlocal calls
            calls += 1
            if calls < 3:
                raise TransientError("temporary")
            return x + offset

        self.assertEqual(work(2, offset=5), 7)
        self.assertEqual(calls, 3)
        self.assertEqual(waits, [0.1, 0.15])
        self.assertEqual(work.__name__, "work")
        self.assertEqual(work.__doc__, "Example metadata.")

    def test_exhaustion_reraises_original_without_final_sleep(self):
        error = TransientError("temporary")
        waits = []
        calls = 0

        @retry(attempts=3, sleep=waits.append)
        def fail():
            nonlocal calls
            calls += 1
            raise error

        with self.assertRaises(TransientError) as result:
            fail()
        self.assertIs(result.exception, error)
        self.assertEqual(calls, 3)
        self.assertEqual(len(waits), 2)

    def test_non_retryable_failure_is_not_retried(self):
        calls = 0

        @retry(attempts=3)
        def fail():
            nonlocal calls
            calls += 1
            raise ValueError("invalid input")

        with self.assertRaises(ValueError):
            fail()
        self.assertEqual(calls, 1)

    def test_invalid_configuration(self):
        for kwargs in (
            {"attempts": 0},
            {"base_delay": -1},
            {"max_delay": float("nan")},
        ):
            with self.assertRaises(ValueError):
                retry(**kwargs)


class DataTests(unittest.TestCase):
    def test_large_stream_and_exhaustion(self):
        stream = generated_tickets(100_000)
        self.assertEqual(summarize(stream), {"open": 50_000, "closed": 50_000})
        self.assertEqual(list(stream), [])

    def test_lazy_read_and_error_chain(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "tickets.jsonl"
            path.write_text(
                '{"ticket_id":"T1","status":"open"}\n\nnot-json\n', encoding="utf-8"
            )
            stream = read_tickets(path)
            self.assertEqual(next(stream).ticket_id, "T1")
            with self.assertRaises(DataError) as caught:
                next(stream)
            self.assertIn("line 3", str(caught.exception))
            self.assertIsNotNone(caught.exception.__cause__)
            # read_tickets has exited and released the file handle on error.
            path.unlink()

    def test_runtime_validation(self):
        for value in (
            [],
            {},
            {"ticket_id": 7, "status": "open"},
            {"ticket_id": "T1", "status": "other"},
        ):
            with self.assertRaises(DataError):
                parse_ticket(value)

    def test_empty_and_negative(self):
        self.assertEqual(summarize(generated_tickets(0)), {"open": 0, "closed": 0})
        with self.assertRaises(ValueError):
            next(generated_tickets(-1))


class ConfigAndLoggingTests(unittest.TestCase):
    def tearDown(self):
        close_logging()

    def test_config_and_secret_repr(self):
        config = Config.from_env(
            {"TICKETKIT_ATTEMPTS": "4", "TICKETKIT_API_TOKEN": "test-placeholder"}
        )
        self.assertEqual(config.attempts, 4)
        self.assertNotIn("test-placeholder", repr(config))
        with self.assertRaises(ConfigError) as caught:
            Config.from_env({"TICKETKIT_ATTEMPTS": "wrong"})
        self.assertIsInstance(caught.exception.__cause__, ValueError)
        with self.assertRaises(ConfigError):
            Config.from_env({"TICKETKIT_ATTEMPTS": "0"})

    def test_context_cleanup(self):
        before = request_id.get()
        with self.assertRaises(ValueError), request_scope("outer"):
            with request_scope("inner"):
                self.assertEqual(request_id.get(), "inner")
            self.assertEqual(request_id.get(), "outer")
            raise ValueError("test")
        self.assertEqual(request_id.get(), before)

    def test_rotation_console_file_and_idempotent_setup(self):
        with (
            tempfile.TemporaryDirectory() as directory,
            patch("sys.stderr", new_callable=io.StringIO) as console,
        ):
            path = Path(directory) / "demo.log"
            setup_logging(path, max_bytes=400)
            logger = setup_logging(path, max_bytes=400)
            self.assertEqual(len(logger.handlers), 2)
            with request_scope("request-007"):
                for index in range(20):
                    logger.info("event=%d", index)
            close_logging()
            self.assertTrue(Path(str(path) + ".1").exists())
            self.assertIn("request_id=request-007", path.read_text(encoding="utf-8"))
            self.assertIn("event=19", console.getvalue())

    def test_timer_success_and_exception(self):
        @timed
        def add(a: int, b: int) -> int:
            return a + b

        with self.assertLogs("ticketkit", level="INFO") as output:
            self.assertEqual(add(2, 3), 5)
            with self.assertRaisesRegex(ValueError, "test"), timed_block("failure"):
                raise ValueError("test")
        self.assertTrue(any("elapsed=" in row for row in output.output))
        self.assertTrue(any("Traceback" in row for row in output.output))


class AsyncTests(unittest.IsolatedAsyncioTestCase):
    def tearDown(self):
        close_logging()

    async def test_order_and_timeout(self):
        async def fake(name, delay):
            if name == "slow":
                raise TimeoutError("controlled timeout")
            return f"{name}:ok"

        with patch("ticketkit.async_tools.simulated_tool", side_effect=fake):
            result = await run_parallel([("first", 0), ("slow", 0), ("last", 0)])
        self.assertEqual(result, ["first:ok", "slow:timeout", "last:ok"])

    async def test_real_timeout_and_cancellation(self):
        finished = asyncio.Event()

        async def never_finishes(name, delay):
            try:
                await asyncio.Event().wait()
            finally:
                finished.set()

        with patch("ticketkit.async_tools.simulated_tool", side_effect=never_finishes):
            result = await run_parallel([("slow", 0)], timeout=0.01)
        self.assertEqual(result, ["slow:timeout"])
        self.assertTrue(finished.is_set())

    async def test_bounded_concurrency_and_request_context(self):
        active = peak = 0
        seen = []

        async def fake(name, delay):
            nonlocal active, peak
            active += 1
            peak = max(active, peak)
            seen.append((name, request_id.get()))
            await asyncio.sleep(0)
            active -= 1
            return name

        with patch("ticketkit.async_tools.simulated_tool", side_effect=fake):
            self.assertEqual(
                await run_parallel([("a", 0), ("b", 0), ("c", 0)], concurrency=2),
                ["a", "b", "c"],
            )
        self.assertLessEqual(peak, 2)
        self.assertTrue(all(name == context for name, context in seen))

    async def test_parent_cancel_is_not_swallowed(self):
        entered = asyncio.Event()

        async def pending(name, delay):
            entered.set()
            await asyncio.Event().wait()

        with patch("ticketkit.async_tools.simulated_tool", side_effect=pending):
            task = asyncio.create_task(run_parallel([("a", 0)], timeout=10))
            await entered.wait()
            task.cancel()
            with self.assertRaises(asyncio.CancelledError):
                await task


if __name__ == "__main__":
    unittest.main()
