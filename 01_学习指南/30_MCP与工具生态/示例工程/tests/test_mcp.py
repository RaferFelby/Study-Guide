import io
import json

import pytest

from catalog import INTERNAL_URI, PUBLIC_URI, read_record
from client import RemoteError, StdioClient
from demo import run_demo
from protocol import (
    CAPABILITIES_KEY,
    CLIENT_INFO_KEY,
    MAX_MESSAGE_BYTES,
    VERSION_KEY,
    PolicyServer,
    build_request,
)
from server import serve


def call(server, method, params=None):
    return server.handle(build_request(1, method, params))


def test_discovery_has_version_capabilities_identity_and_no_session_state():
    server = PolicyServer()
    response = call(server, "server/discover")["result"]
    assert response["supportedVersions"] == ["2026-07-28"]
    assert set(response["capabilities"]) == {"tools", "resources", "prompts"}
    assert response["ttlMs"] == 0 and response["cacheScope"] == "private"
    assert call(PolicyServer(), "tools/list")["result"]["tools"]


@pytest.mark.parametrize("mutation", ["params", "meta", "version", "capabilities"])
def test_each_request_requires_metadata(mutation):
    request = build_request(4, "ping")
    if mutation == "params":
        request.pop("params")
    elif mutation == "meta":
        request["params"].pop("_meta")
    elif mutation == "version":
        request["params"]["_meta"].pop(VERSION_KEY)
    else:
        request["params"]["_meta"].pop(CAPABILITIES_KEY)
    response = PolicyServer().handle(request)
    assert response["id"] == 4 and response["error"]["code"] == -32602


def test_version_mismatch_reports_modern_error_and_supported_list():
    response = PolicyServer().handle(
        build_request("version-1", "server/discover", version="2025-11-25")
    )
    assert response["error"]["code"] == -32022
    assert response["error"]["data"] == {
        "supported": ["2026-07-28"],
        "requested": "2025-11-25",
    }
    assert call(PolicyServer(), "initialize")["error"]["code"] == -32601


@pytest.mark.parametrize("value", [None, True, [], {}, ""])
def test_invalid_id_is_not_accepted_as_valid_request(value):
    request = build_request(value, "ping")
    response = PolicyServer().handle(request)
    assert response["error"]["code"] == -32600 and "id" not in response


def test_notification_does_not_get_response():
    assert (
        PolicyServer().handle({"jsonrpc": "2.0", "method": "notifications/cancelled"})
        is None
    )


def test_tool_schema_call_and_resource_agree():
    server = PolicyServer()
    tool = call(server, "tools/list")["result"]["tools"][0]
    assert tool["inputSchema"]["additionalProperties"] is False
    result = call(
        server, "tools/call", {"name": "get_policy", "arguments": {"topic": "refund"}}
    )["result"]
    assert result["isError"] is False
    assert json.loads(result["content"][0]["text"]) == result["structuredContent"]
    resource = call(server, "resources/read", {"uri": PUBLIC_URI})["result"]
    assert json.loads(resource["contents"][0]["text"]) == result["structuredContent"]
    assert result["structuredContent"]["version"] == "v1"


@pytest.mark.parametrize(
    "arguments",
    [
        {},
        {"topic": True},
        {"topic": "invoice"},
        {"topic": "refund", "path": "../secret"},
        [],
    ],
)
def test_tool_arguments_reject_missing_extra_wrong_value_and_type(arguments):
    response = call(
        PolicyServer(), "tools/call", {"name": "get_policy", "arguments": arguments}
    )
    assert response["error"]["code"] == -32602


def test_guest_discovery_is_filtered_but_direct_call_is_also_denied(monkeypatch):
    server = PolicyServer("guest")
    assert [tool["name"] for tool in call(server, "tools/list")["result"]["tools"]] == [
        "get_policy"
    ]
    assert [
        resource["uri"]
        for resource in call(server, "resources/list")["result"]["resources"]
    ] == [PUBLIC_URI]

    def forbidden_read(uri):
        raise AssertionError("拒绝路径不能读取内部资料")

    monkeypatch.setattr("protocol.read_record", forbidden_read)
    request = build_request(
        1, "tools/call", {"name": "get_support_note", "arguments": {}}
    )
    request["params"]["_meta"][CLIENT_INFO_KEY] = {"name": "admin", "version": "999"}
    result = server.handle(request)["result"]
    assert result["isError"] is True
    assert (
        call(server, "resources/read", {"uri": INTERNAL_URI})["error"]["code"] == 1001
    )


@pytest.mark.parametrize(
    "uri",
    [
        "file:///C:/Windows/system.ini",
        "knowledge://public/../internal/support-v1",
        "https://example.com/data",
        "knowledge://missing",
    ],
)
def test_resource_uri_cannot_become_arbitrary_file_or_network_read(uri):
    with pytest.raises(ValueError):
        read_record(uri)
    assert (
        call(PolicyServer(), "resources/read", {"uri": uri})["error"]["code"] == -32602
    )


def test_prompt_preparation_has_user_message_without_tool_execution(monkeypatch):
    def forbidden_read(uri):
        raise AssertionError("提示读取不得自动执行工具")

    monkeypatch.setattr("protocol.read_record", forbidden_read)
    result = call(
        PolicyServer(),
        "prompts/get",
        {"name": "policy_question", "arguments": {"question": "退款？"}},
    )["result"]
    assert result["messages"][0]["role"] == "user"
    assert result["messages"][0]["content"]["text"].endswith("退款？")
    assert call(PolicyServer(), "prompts/list")["result"]["prompts"][0]["arguments"][0][
        "required"
    ]
    assert (
        call(
            PolicyServer(), "prompts/get", {"name": "policy_question", "arguments": {}}
        )["error"]["code"]
        == -32602
    )


def test_unavailable_is_tool_error_but_resource_rpc_application_error():
    server = PolicyServer(mode="unavailable")
    assert (
        call(
            server,
            "tools/call",
            {"name": "get_policy", "arguments": {"topic": "refund"}},
        )["result"]["isError"]
        is True
    )
    assert call(server, "resources/read", {"uri": PUBLIC_URI})["error"]["code"] == 1002


def test_parse_error_does_not_pollute_stdout_and_next_request_works():
    valid = (json.dumps(build_request(9, "ping")) + "\n").encode("utf-8")
    output = io.BytesIO()
    serve(io.BytesIO(b"not json\n" + valid), output, PolicyServer())
    responses = [json.loads(line) for line in output.getvalue().splitlines()]
    assert responses[0]["error"]["code"] == -32700
    assert (
        responses[1]["id"] == 9 and responses[1]["result"]["resultType"] == "complete"
    )


def test_oversize_message_is_rejected_and_stream_stops():
    output = io.BytesIO()
    serve(io.BytesIO(b"x" * (MAX_MESSAGE_BYTES + 1) + b"\n"), output, PolicyServer())
    assert json.loads(output.getvalue())["error"]["code"] == -32600


def test_real_stdio_unicode_rpc_error_recovery_and_shutdown():
    with StdioClient() as client:
        result = client.request("resources/read", {"uri": PUBLIC_URI})
        assert "模拟" in result["contents"][0]["text"]
        with pytest.raises(RemoteError) as raised:
            client.request("unknown/method")
        assert raised.value.code == -32601
        assert client.request("ping")["resultType"] == "complete"
        process = client.process
    assert process.poll() == 0 and process.stdin.closed and process.stdout.closed
    assert not client.reader.is_alive()


@pytest.mark.parametrize(
    "fault", ["log_stdout", "wrong_id", "bad_result", "exit", "timeout", "oversize"]
)
def test_bad_stdio_peer_closes_owned_process(tmp_path, fault):
    actions = {
        "log_stdout": "print('debug text',flush=True)",
        "wrong_id": "print(json.dumps({'jsonrpc':'2.0','id':999,'result':{'resultType':'complete'}}),flush=True)",
        "bad_result": "print(json.dumps({'jsonrpc':'2.0','id':1,'result':{},'error':{}}),flush=True)",
        "exit": "raise SystemExit(3)",
        "timeout": "time.sleep(5)",
        "oversize": "print('x'*40000,flush=True)",
    }
    path = tmp_path / "fake_server.py"
    path.write_text(
        "import sys,json,time\nsys.stdin.readline()\n" + actions[fault] + "\n",
        encoding="utf-8",
    )
    with StdioClient(server_path=path, timeout_seconds=0.15) as client:
        with pytest.raises((ConnectionError, TimeoutError)):
            client.request("ping")
        assert client.process.poll() is not None
    assert not client.reader.is_alive()


@pytest.mark.parametrize("timeout", [0, -1, True, float("inf"), 11])
def test_invalid_timeout_is_rejected_before_process_start(timeout):
    with pytest.raises(ValueError):
        StdioClient(timeout_seconds=timeout)


def test_complete_demo_reports_synthetic_identity_and_no_model():
    report = run_demo()
    assert report["all_children_exited"] and report["connection_alive_after_rpc_error"]
    assert (
        report["llm_called"] is False
        and report["external_application_connected"] is False
    )
    assert report["guest_tools"] == ["get_policy"]
    assert (
        report["permission_tool_is_error"]
        and report["permission_resource_code"] == 1001
    )
