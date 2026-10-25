"""实际本地stdio发现/调用/读取/拒绝，报告不覆盖已有文件。"""

import argparse
import json
from pathlib import Path

from catalog import INTERNAL_URI, PUBLIC_URI
from client import RemoteError, StdioClient


def run_demo():
    with StdioClient() as client:
        discovered = client.request("server/discover")
        tools = client.request("tools/list")
        policy = client.request(
            "tools/call", {"name": "get_policy", "arguments": {"topic": "refund"}}
        )
        resource = client.request("resources/read", {"uri": PUBLIC_URI})
        prompt = client.request(
            "prompts/get",
            {"name": "policy_question", "arguments": {"question": "退款期限是多少？"}},
        )
        try:
            client.request(
                "tools/call", {"name": "get_policy", "arguments": {"topic": "unknown"}}
            )
        except RemoteError as error:
            invalid_code = error.code
        else:
            raise AssertionError("非法参数未被拒绝")
        healthy_after_error = client.request("ping")["resultType"] == "complete"
        reader_process = client.process
    with StdioClient(audience="guest") as guest:
        guest_tools = guest.request("tools/list")["tools"]
        denied = guest.request(
            "tools/call", {"name": "get_support_note", "arguments": {}}
        )
        try:
            guest.request("resources/read", {"uri": INTERNAL_URI})
        except RemoteError as error:
            denied_resource_code = error.code
        else:
            raise AssertionError("内部资源未被拒绝")
        guest_process = guest.process
    with StdioClient(mode="unavailable") as unavailable:
        unavailable_result = unavailable.request(
            "tools/call", {"name": "get_policy", "arguments": {"topic": "refund"}}
        )
        unavailable_process = unavailable.process
    assert policy["isError"] is False and denied["isError"] is True
    assert unavailable_result["isError"] is True
    assert invalid_code == -32602 and denied_resource_code == 1001
    assert all(
        process.poll() == 0
        for process in (reader_process, guest_process, unavailable_process)
    )
    return {
        "scope": "real_local_stdio_limited_mcp_subset_with_synthetic_data",
        "protocol_version": discovered["supportedVersions"][0],
        "reader_tools": [tool["name"] for tool in tools["tools"]],
        "guest_tools": [tool["name"] for tool in guest_tools],
        "policy": policy["structuredContent"],
        "resource_uri": resource["contents"][0]["uri"],
        "prompt_only": prompt["messages"][0]["content"]["text"],
        "invalid_params_code": invalid_code,
        "permission_tool_is_error": denied["isError"],
        "permission_resource_code": denied_resource_code,
        "unavailable_tool_is_error": unavailable_result["isError"],
        "connection_alive_after_rpc_error": healthy_after_error,
        "all_children_exited": True,
        "llm_called": False,
        "external_application_connected": False,
        "authentication": "trusted_demo_startup_configuration_not_real_identity",
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=Path("report-my-01.json"))
    args = parser.parse_args()
    if args.output.exists():
        raise FileExistsError("选择新的报告文件名，不覆盖已有学习记录")
    report = run_demo()
    with args.output.open("x", encoding="utf-8") as file:
        json.dump(report, file, ensure_ascii=False, indent=2)
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
