"""用 Python 标准库调用 Responses 风格 HTTP 接口，并提供有限重试与内存缓存。"""

from collections.abc import Callable, MutableMapping
from dataclasses import dataclass
from hashlib import sha256
from json import dumps, loads
from time import monotonic, sleep
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

RETRYABLE_STATUS_CODES = {429, 500, 502, 503, 504}


class ApiError(RuntimeError):
    """API 请求失败，错误文本不包含请求密钥。"""


@dataclass(frozen=True)
class ApiResult:
    response: dict[str, Any]
    attempts: int
    elapsed_ms: float
    cache_hit: bool


def _request_key(base_url: str, body: bytes, api_key: str) -> str:
    """按 endpoint、凭证作用域和正文生成稳定 key，不保存原始密钥。"""
    credential_scope = sha256(api_key.encode("utf-8")).digest()
    return sha256(
        base_url.rstrip("/").encode("utf-8") + b"\n" + credential_scope + b"\n" + body
    ).hexdigest()


def call_api(
    base_url: str,
    payload: dict[str, Any],
    api_key: str,
    *,
    timeout_seconds: float = 5.0,
    max_attempts: int = 3,
    backoff_seconds: float = 0.1,
    cache: MutableMapping[str, dict[str, Any]] | None = None,
    sleep_function: Callable[[float], None] = sleep,
) -> ApiResult:
    """发送 JSON POST；只对临时错误做有限重试，成功结果可选缓存。"""
    if not base_url.startswith(("http://", "https://")):
        raise ValueError("base_url 必须以 http:// 或 https:// 开头")
    if not api_key:
        raise ValueError("api_key 不能为空")
    if timeout_seconds <= 0:
        raise ValueError("timeout_seconds 必须大于 0")
    if max_attempts < 1:
        raise ValueError("max_attempts 至少为 1")
    if max_attempts > 10:
        raise ValueError("max_attempts 不能超过 10")
    if backoff_seconds < 0:
        raise ValueError("backoff_seconds 不能小于 0")

    body = dumps(
        payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")
    idempotency_key = _request_key(base_url, body, api_key)
    if cache is not None and idempotency_key in cache:
        return ApiResult(
            cache[idempotency_key], attempts=0, elapsed_ms=0.0, cache_hit=True
        )

    request = Request(
        url=f"{base_url.rstrip('/')}/v1/responses",
        data=body,
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
            "Idempotency-Key": idempotency_key,
        },
        method="POST",
    )

    for attempt in range(1, max_attempts + 1):
        started_at = monotonic()
        try:
            with urlopen(request, timeout=timeout_seconds) as response:
                response_body = response.read()
            try:
                response_data = loads(response_body)
            except (UnicodeDecodeError, ValueError) as error:
                raise ApiError("API 响应不是有效 JSON") from error
            if not isinstance(response_data, dict):
                raise ApiError("API 响应 JSON 顶层必须是对象")
            elapsed_ms = (monotonic() - started_at) * 1000
            if cache is not None:
                cache[idempotency_key] = response_data
            return ApiResult(response_data, attempt, elapsed_ms, cache_hit=False)
        except HTTPError as error:
            should_retry = error.code in RETRYABLE_STATUS_CODES
            if not should_retry or attempt == max_attempts:
                raise ApiError(
                    f"API 返回 HTTP {error.code}，已尝试 {attempt} 次"
                ) from error
        except (TimeoutError, URLError) as error:
            if attempt == max_attempts:
                raise ApiError(f"API 连接失败，已尝试 {attempt} 次") from error

        delay_seconds = min(backoff_seconds * (2 ** (attempt - 1)), 5.0)
        sleep_function(delay_seconds)

    raise ApiError("API 请求未能完成")


def extract_output_text(response: dict[str, Any]) -> str:
    """从响应的 message/content 项提取文本，不假设第一个输出就是文本。"""
    output_items = response.get("output")
    if not isinstance(output_items, list):
        raise ApiError("响应缺少 output 列表")

    text_parts: list[str] = []
    for item in output_items:
        if not isinstance(item, dict) or item.get("type") != "message":
            continue
        if item.get("role") != "assistant":
            continue
        content_parts = item.get("content")
        if not isinstance(content_parts, list):
            continue
        for part in content_parts:
            if isinstance(part, dict) and part.get("type") == "output_text":
                text_value = part.get("text")
                if isinstance(text_value, str):
                    text_parts.append(text_value)

    if not text_parts:
        raise ApiError("响应中没有 assistant output_text")
    return "".join(text_parts)
