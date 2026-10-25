import pytest

from api_client import ApiError, call_api, extract_output_text
from fake_provider import _FakeProviderHandler, run_fake_provider


def test_local_api_returns_text_and_usage():
    with run_fake_provider() as base_url:
        result = call_api(
            base_url,
            {"model": "demo", "input": "申请退款"},
            "not-a-real-key",
        )

    assert result.response["usage"]["input_tokens"] > 0
    assert extract_output_text(result.response).startswith('{"category":"refund"')
    assert result.attempts == 1
    assert result.cache_hit is False


def test_retry_reuses_idempotency_key_and_stops_after_success():
    with run_fake_provider() as base_url:
        result = call_api(
            base_url,
            {"model": "demo", "input": "retry-once"},
            "not-a-real-key",
            backoff_seconds=0,
            sleep_function=lambda _: None,
        )

    assert result.attempts == 2
    assert max(_FakeProviderHandler.request_counts.values()) == 2


def test_retry_is_bounded_for_repeated_rate_limit():
    with (
        run_fake_provider() as base_url,
        pytest.raises(ApiError, match="HTTP 429.*2 次"),
    ):
        call_api(
            base_url,
            {"model": "demo", "input": "always-rate-limit"},
            "not-a-real-key",
            max_attempts=2,
            backoff_seconds=0,
            sleep_function=lambda _: None,
        )

    assert max(_FakeProviderHandler.request_counts.values()) == 2


def test_bad_request_is_not_retried():
    with (
        run_fake_provider() as base_url,
        pytest.raises(ApiError, match="HTTP 400.*1 次"),
    ):
        call_api(
            base_url,
            {"model": "demo", "input": "bad-request"},
            "not-a-real-key",
            max_attempts=3,
            backoff_seconds=0,
            sleep_function=lambda _: None,
        )

    assert max(_FakeProviderHandler.request_counts.values()) == 1


def test_success_can_be_cached_and_cache_key_changes_with_payload():
    cache = {}
    payload = {"model": "demo", "input": "申请退款"}
    with run_fake_provider() as base_url:
        first = call_api(base_url, payload, "not-a-real-key", cache=cache)
        second = call_api(base_url, payload, "not-a-real-key", cache=cache)
        changed = call_api(
            base_url,
            {"model": "demo", "input": "其他问题"},
            "not-a-real-key",
            cache=cache,
        )

    assert first.cache_hit is False
    assert second.cache_hit is True
    assert changed.cache_hit is False
    assert len(_FakeProviderHandler.request_counts) == 2


@pytest.mark.parametrize(
    "kwargs, message",
    [
        ({"base_url": "local", "max_attempts": 1}, "base_url"),
        ({"base_url": "http://localhost", "timeout_seconds": 0}, "timeout_seconds"),
        ({"base_url": "http://localhost", "max_attempts": 0}, "max_attempts"),
        ({"base_url": "http://localhost", "max_attempts": 11}, "不能超过 10"),
        ({"base_url": "http://localhost", "backoff_seconds": -1}, "backoff_seconds"),
    ],
)
def test_invalid_client_configuration_is_rejected(kwargs, message):
    options = {"base_url": "http://localhost", **kwargs}
    options.pop("api_key", None)
    with pytest.raises(ValueError, match=message):
        call_api(api_key="demo", payload={}, **options)


def test_missing_api_key_is_rejected():
    with pytest.raises(ValueError, match="api_key"):
        call_api("http://localhost", {}, "")


def test_extract_output_text_does_not_assume_first_output_is_text():
    response = {
        "output": [
            {"type": "reasoning", "summary": []},
            {
                "type": "message",
                "role": "assistant",
                "content": [{"type": "output_text", "text": "answer"}],
            },
        ]
    }

    assert extract_output_text(response) == "answer"


def test_extract_output_text_reports_missing_text():
    with pytest.raises(ApiError, match="没有 assistant output_text"):
        extract_output_text({"output": []})


def test_cache_scope_changes_when_api_key_changes():
    cache = {}
    payload = {"model": "demo", "input": "申请退款"}
    with run_fake_provider() as base_url:
        call_api(base_url, payload, "first-demo-key", cache=cache)
        second = call_api(base_url, payload, "different-demo-key", cache=cache)

    assert second.cache_hit is False
    assert len(_FakeProviderHandler.request_counts) == 2
