import json

import pytest

from contracts import (
    TOOL_SCHEMAS,
    ToolCall,
    ToolContext,
    parse_arguments,
    validate_arguments,
)
from evaluation import evaluate_selector
from messages import execute_calls, make_assistant_message, validate_tool_message
from runtime import ToolRuntime, call_fingerprint


@pytest.mark.parametrize(
    "text", ["{", "[]", '{"query":"a","query":"b"}', '{"number":NaN}', "x" * 8193]
)
def test_argument_parser_rejects_invalid_json(text):
    with pytest.raises((ValueError, TypeError)):
        parse_arguments(text)


@pytest.mark.parametrize(
    "arguments",
    [
        {"query": "storage"},
        {"query": "", "top_k": 1},
        {"query": "storage", "top_k": True},
        {"query": "storage", "top_k": "1"},
        {"query": "storage", "top_k": 0},
        {"query": "storage", "top_k": 6},
        {"query": "storage", "top_k": 1, "role": "staff"},
    ],
)
def test_schema_checks_missing_type_range_and_extra_fields(arguments):
    with pytest.raises(ValueError):
        validate_arguments(arguments, TOOL_SCHEMAS["search_policies"]["parameters"])


def test_public_context_never_returns_private_document():
    runtime = ToolRuntime()
    result = runtime.execute(
        ToolCall("q1", "search_policies", '{"query":"retention","top_k":5}'),
        ToolContext("visitor", "public"),
    )
    assert result["ok"]
    assert len(result["data"]["evidence"]) == 2
    assert all(
        item["id"] != "database-retention" for item in result["data"]["evidence"]
    )


def test_no_match_is_successful_empty_search_not_exception():
    result = ToolRuntime().execute(
        ToolCall("q", "search_policies", '{"query":"unknown","top_k":1}'),
        ToolContext("user", "staff"),
    )
    assert result["ok"]
    assert result["data"]["evidence"] == []


def test_invalid_arguments_are_returned_as_structured_error():
    result = ToolRuntime().execute(
        ToolCall("q", "search_policies", '{"query":"storage","top_k":true}'),
        ToolContext("user", "staff"),
    )
    assert result["error"]["code"] == "invalid_arguments"
    assert result["error"]["retryable"] is False


def test_writes_require_permission_confirmation_and_deduplicate():
    runtime = ToolRuntime()
    arguments = {"title": "example", "idempotency_key": "request-1"}
    call = ToolCall("w", "create_ticket", json.dumps(arguments))
    staff = ToolContext("user", "staff")
    assert (
        runtime.execute(call, ToolContext("user", "public"))["error"]["code"]
        == "permission_denied"
    )
    assert runtime.execute(call, staff)["error"]["code"] == "confirmation_required"
    assert runtime.tickets == []
    fingerprint = call_fingerprint(call.name, arguments, staff.actor_id)
    approved = ToolContext("user", "staff", frozenset({fingerprint}))
    first = runtime.execute(call, approved)
    second = runtime.execute(
        ToolCall("another-call-id", call.name, call.arguments_json), staff
    )
    assert first == second
    assert len(runtime.tickets) == 1
    first["data"]["title"] = "caller changed output"
    assert runtime.tickets[0]["title"] == "example"


def test_idempotency_conflict_and_actor_scope():
    runtime = ToolRuntime()
    arguments = {"title": "first", "idempotency_key": "same-key"}
    fingerprint = call_fingerprint("create_ticket", arguments, "a")
    call = ToolCall("w1", "create_ticket", json.dumps(arguments))
    runtime.execute(call, ToolContext("a", "staff", frozenset({fingerprint})))
    changed = {**arguments, "title": "different"}
    conflict = runtime.execute(
        ToolCall("w2", "create_ticket", json.dumps(changed)), ToolContext("a", "staff")
    )
    assert conflict["error"]["code"] == "idempotency_conflict"
    other_actor = runtime.execute(call, ToolContext("b", "staff"))
    assert other_actor["error"]["code"] == "confirmation_required"
    assert len(runtime.tickets) == 1


def test_revoked_permission_blocks_cached_result():
    runtime = ToolRuntime()
    arguments = {"title": "first", "idempotency_key": "same-key"}
    fingerprint = call_fingerprint("create_ticket", arguments, "a")
    call = ToolCall("w1", "create_ticket", json.dumps(arguments))
    runtime.execute(call, ToolContext("a", "staff", frozenset({fingerprint})))
    result = runtime.execute(call, ToolContext("a", "public"))
    assert result["error"]["code"] == "permission_denied"


def test_messages_match_each_call_and_consume_pending_id():
    calls = [ToolCall("q", "search_policies", '{"query":"storage","top_k":1}')]
    assert make_assistant_message(calls)["role"] == "assistant"
    messages = execute_calls(calls, ToolRuntime(), ToolContext("a", "staff"))
    pending = {"q"}
    validate_tool_message(messages[0], pending)
    assert pending == set()
    with pytest.raises(ValueError):
        validate_tool_message(messages[0], pending)


def test_duplicate_call_ids_are_rejected_before_side_effect():
    call = ToolCall("same", "create_ticket", '{"title":"x","idempotency_key":"k"}')
    runtime = ToolRuntime()
    with pytest.raises(ValueError):
        execute_calls([call, call], runtime, ToolContext("a", "staff"))
    assert runtime.tickets == []


def test_result_truncation_is_explicit():
    result = ToolRuntime().execute(
        ToolCall("q", "search_policies", '{"query":"retention","top_k":1}'),
        ToolContext("a", "staff"),
    )
    assert result["data"]["matched_count"] == 3
    assert result["data"]["truncated"] is True
    assert len(result["data"]["evidence"]) == 1


def test_unknown_tool_and_empty_call_id_are_errors():
    runtime = ToolRuntime()
    context = ToolContext("a", "staff")
    assert (
        runtime.execute(ToolCall("q", "invented", "{}"), context)["error"]["code"]
        == "unknown_tool"
    )
    assert (
        runtime.execute(ToolCall("", "search_policies", "{}"), context)["error"]["code"]
        == "invalid_call_id"
    )


def test_selector_metrics_expose_argument_failure():
    report = evaluate_selector()
    assert report["tool_selection_accuracy"] == 1
    assert report["argument_accuracy"] == 0.75
    assert report["task_completion_rate"] == 0.75
