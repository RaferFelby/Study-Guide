"""有界异步工具调度；仅本地协作式协程，不是隔离进程。"""

import asyncio
import hashlib
import json
import math
from collections.abc import Awaitable, Callable
from copy import deepcopy
from dataclasses import dataclass
from time import monotonic, perf_counter


@dataclass(frozen=True)
class Request:
    call_id: str
    tool_name: str
    arguments: dict


@dataclass(frozen=True)
class ToolSpec:
    execute: Callable[[dict], Awaitable[dict]]
    is_read_only: bool = False
    is_idempotent: bool = False

    @property
    def safe_to_retry(self) -> bool:
        return self.is_read_only or self.is_idempotent


class RateLimitedError(Exception):
    def __init__(self, retry_after_seconds: float):
        if not math.isfinite(retry_after_seconds) or retry_after_seconds < 0:
            raise ValueError("Retry-After 必须是有限非负时间")
        super().__init__("上游限流")
        self.retry_after_seconds = retry_after_seconds


class CircuitBreaker:
    def __init__(
        self,
        failure_threshold: int = 2,
        cooldown_seconds: float = 1.0,
        clock: Callable[[], float] = monotonic,
    ):
        if (
            failure_threshold < 1
            or not math.isfinite(cooldown_seconds)
            or cooldown_seconds <= 0
        ):
            raise ValueError("熔断阈值和冷却时间必须大于0")
        self.failure_threshold = failure_threshold
        self.cooldown_seconds = cooldown_seconds
        self.clock = clock
        self.failures = {}
        self.open_until = {}

    def allows(self, tool_name: str) -> bool:
        deadline = self.open_until.get(tool_name)
        if deadline is None:
            return True
        if self.clock() < deadline:
            return False
        self.open_until.pop(tool_name)
        self.failures[tool_name] = 0
        return True

    def record_success(self, tool_name: str) -> None:
        self.failures[tool_name] = 0

    def record_failure(self, tool_name: str) -> None:
        count = self.failures.get(tool_name, 0) + 1
        self.failures[tool_name] = count
        if count >= self.failure_threshold:
            self.open_until[tool_name] = self.clock() + self.cooldown_seconds


def error_result(
    code: str, message: str, attempts: int = 0, retryable: bool = False
) -> dict:
    return {
        "ok": False,
        "data": None,
        "attempts": attempts,
        "error": {"code": code, "message": message, "retryable": retryable},
    }


class Scheduler:
    def __init__(
        self,
        tools: dict[str, ToolSpec],
        max_concurrency: int = 2,
        timeout_seconds: float = 0.2,
        max_attempts: int = 2,
        base_delay_seconds: float = 0.01,
        max_delay_seconds: float = 0.2,
        rate_interval_seconds: float = 0.0,
        max_calls: int = 20,
        max_output_characters: int = 300,
        breaker: CircuitBreaker | None = None,
    ):
        if (
            max_concurrency < 1
            or max_attempts < 1
            or max_calls < 1
            or max_output_characters < 1
        ):
            raise ValueError("并发/重试/批大小/输出预算必须大于0")
        if (
            timeout_seconds <= 0
            or base_delay_seconds < 0
            or max_delay_seconds < 0
            or rate_interval_seconds < 0
        ):
            raise ValueError("超时必须大于0，等待时间不能小于0")
        if not all(
            math.isfinite(value)
            for value in [
                timeout_seconds,
                base_delay_seconds,
                max_delay_seconds,
                rate_interval_seconds,
            ]
        ):
            raise ValueError("时间参数必须是有限值")
        self.tools = tools
        self.semaphore = asyncio.Semaphore(max_concurrency)
        self.rate_lock = asyncio.Lock()
        self.next_start = 0.0
        self.timeout_seconds = timeout_seconds
        self.max_attempts = max_attempts
        self.base_delay_seconds = base_delay_seconds
        self.max_delay_seconds = max_delay_seconds
        self.rate_interval_seconds = rate_interval_seconds
        self.max_calls = max_calls
        self.max_output_characters = max_output_characters
        self.breaker = breaker or CircuitBreaker()
        self.full_results = {}

    async def run_batch(
        self, requests: list[Request], parallel: bool = True
    ) -> list[dict]:
        if len(requests) > self.max_calls:
            raise ValueError("批次超过接收上限，请拆批或等待；未执行任何工具")
        ids = [request.call_id for request in requests]
        if any(not isinstance(item, str) or not item.strip() for item in ids):
            raise ValueError("call_id 必须非空且唯一")
        if len(ids) != len(set(ids)):
            raise ValueError("call_id 不能重复")
        keys = []
        for request in requests:
            if not isinstance(request.tool_name, str) or not isinstance(
                request.arguments, dict
            ):
                raise TypeError("工具名必须为字符串、参数必须为dict")
            keys.append(
                json.dumps(
                    {"tool": request.tool_name, "arguments": request.arguments},
                    sort_keys=True,
                    ensure_ascii=False,
                    allow_nan=False,
                )
            )
        tasks = {}
        serial_results = {}
        answers = []
        try:
            for request, key in zip(requests, keys):
                spec = self.tools.get(request.tool_name)
                # 仅安全操作同批去重。非幂等写即使参数相同，也不自动视为同一业务请求。
                share_key = (
                    ("safe", key)
                    if spec is not None and spec.safe_to_retry
                    else ("unsafe", request.call_id)
                )
                if parallel:
                    if share_key not in tasks:
                        tasks[share_key] = asyncio.create_task(self._execute(request))
                elif share_key not in serial_results:
                    serial_results[share_key] = await self._execute(request)
            if parallel:
                completed = await asyncio.gather(*tasks.values())
                serial_results = dict(zip(tasks, completed))
            for request, key in zip(requests, keys):
                spec = self.tools.get(request.tool_name)
                share_key = (
                    ("safe", key)
                    if spec is not None and spec.safe_to_retry
                    else ("unsafe", request.call_id)
                )
                answers.append(
                    {
                        "call_id": request.call_id,
                        "tool_name": request.tool_name,
                        **deepcopy(serial_results[share_key]),
                    }
                )
        except asyncio.CancelledError:
            for task in tasks.values():
                task.cancel()
            await asyncio.gather(*tasks.values(), return_exceptions=True)
            raise
        except Exception:
            # 非预期程序错误继续抛出，同时收拢其他任务，避免后台继续运行。
            for task in tasks.values():
                task.cancel()
            await asyncio.gather(*tasks.values(), return_exceptions=True)
            raise
        return answers

    async def _wait_for_rate_slot(self) -> None:
        async with self.rate_lock:
            delay = max(0.0, self.next_start - monotonic())
            if delay:
                await asyncio.sleep(delay)
            self.next_start = monotonic() + self.rate_interval_seconds

    async def _execute(self, request: Request) -> dict:
        spec = self.tools.get(request.tool_name)
        if spec is None:
            return error_result("unknown_tool", "工具没有注册")
        if not self.breaker.allows(request.tool_name):
            return error_result("circuit_open", "工具暂时熔断，请降级或稍后再查")
        attempts_limit = self.max_attempts if spec.safe_to_retry else 1
        started = perf_counter()
        for attempt in range(1, attempts_limit + 1):
            retry_after = 0.0
            try:
                async with self.semaphore:
                    if not self.breaker.allows(request.tool_name):
                        return error_result(
                            "circuit_open", "等待期间工具已熔断", attempt - 1
                        )
                    await self._wait_for_rate_slot()
                    data = await asyncio.wait_for(
                        spec.execute(deepcopy(request.arguments)),
                        timeout=self.timeout_seconds,
                    )
                if not isinstance(data, dict):
                    raise TypeError("工具必须返回dict")
                payload = self._limit_output(data)
                self.breaker.record_success(request.tool_name)
                return {
                    "ok": True,
                    "data": payload,
                    "error": None,
                    "attempts": attempt,
                    "elapsed_ms": (perf_counter() - started) * 1000,
                }
            except asyncio.CancelledError:
                raise
            except TimeoutError:
                code = "timeout" if spec.safe_to_retry else "outcome_unknown"
                message = (
                    "工具超时"
                    if spec.safe_to_retry
                    else "非幂等写超时，结果未知，禁止盲重试"
                )
                result = error_result(code, message, attempt, spec.safe_to_retry)
            except RateLimitedError as error:
                retry_after = max(0.0, error.retry_after_seconds)
                result = error_result(
                    "rate_limited", "上游限流", attempt, spec.safe_to_retry
                )
            except OSError:
                code = (
                    "temporary_io_failure" if spec.safe_to_retry else "outcome_unknown"
                )
                result = error_result(
                    code,
                    "外部读写失败，写入结果需另行核实",
                    attempt,
                    spec.safe_to_retry,
                )
            except (ValueError, TypeError, KeyError):
                return error_result(
                    "invalid_arguments_or_result",
                    "参数或返回格式错误，不应原样重试",
                    attempt,
                )
            if attempt == attempts_limit:
                self.breaker.record_failure(request.tool_name)
                result["elapsed_ms"] = (perf_counter() - started) * 1000
                return result
            exponential_delay = self.base_delay_seconds * 2 ** (attempt - 1)
            delay = max(exponential_delay, retry_after)
            if delay > self.max_delay_seconds:
                self.breaker.record_failure(request.tool_name)
                result["error"]["message"] += "；所需等待超过本次预算，停止自动重试"
                return result
            # 退避在并发槽之外，其他独立请求可以继续。
            await asyncio.sleep(delay)
        raise RuntimeError("不应到达的重试分支")

    def _limit_output(self, data: dict) -> dict:
        serialized = json.dumps(data, ensure_ascii=False, allow_nan=False)
        if len(serialized) <= self.max_output_characters:
            return {"is_summary": False, "content": deepcopy(data)}
        result_ref = hashlib.sha256(serialized.encode("utf-8")).hexdigest()
        self.full_results[result_ref] = deepcopy(data)
        return {
            "is_summary": True,
            "preview": serialized[: self.max_output_characters],
            "original_characters": len(serialized),
            "preview_characters": self.max_output_characters,
            "result_ref": result_ref,
            "truncated": True,
            "preview_format": "text",
        }

    def read_full_result(self, result_ref: str) -> dict:
        if result_ref not in self.full_results:
            raise KeyError("结果引用不存在")
        return deepcopy(self.full_results[result_ref])


def merge_facts(results: list[dict]) -> dict:
    facts = {}
    conflicts = []
    failures = []
    for result in results:
        if not result["ok"]:
            failures.append({"call_id": result["call_id"], "error": result["error"]})
            continue
        payload = result["data"]
        if payload["is_summary"]:
            failures.append(
                {"call_id": result["call_id"], "error": {"code": "needs_full_result"}}
            )
            continue
        data = payload["content"]
        if "field" not in data or "value" not in data:
            continue
        field = data["field"]
        if field in facts and facts[field]["value"] != data["value"]:
            conflicts.append({"field": field, "first": facts[field], "second": data})
        else:
            facts[field] = data
    for conflict in conflicts:
        facts.pop(conflict["field"], None)
    return {
        "facts": facts,
        "conflicts": conflicts,
        "failures": failures,
        "is_complete": not conflicts and not failures,
    }
