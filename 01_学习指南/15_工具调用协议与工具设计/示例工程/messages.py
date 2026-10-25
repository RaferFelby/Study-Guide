"""教学内部消息适配：按 call_id 关联请求和 role=tool 返回。"""

import json

from contracts import ToolCall, ToolContext
from runtime import ToolRuntime


def make_assistant_message(calls: list[ToolCall]) -> dict:
    ids = [call.call_id for call in calls]
    if any(
        not isinstance(identifier, str) or not identifier.strip() for identifier in ids
    ):
        raise ValueError("调用ID必须是非空字符串")
    if len(ids) != len(set(ids)):
        raise ValueError("同一批调用ID必须非空且唯一")
    return {
        "role": "assistant",
        "content": None,
        "tool_calls": [
            {"id": call.call_id, "name": call.name, "arguments": call.arguments_json}
            for call in calls
        ],
    }


def execute_calls(
    calls: list[ToolCall], runtime: ToolRuntime, context: ToolContext
) -> list[dict]:
    make_assistant_message(calls)  # 整批先验ID，避免执行一半后才发现重复。
    messages = []
    for call in calls:
        result = runtime.execute(call, context)
        messages.append(
            {
                "role": "tool",
                "tool_call_id": call.call_id,
                "content": json.dumps(result, ensure_ascii=False),
            }
        )
    return messages


def validate_tool_message(message: dict, pending_ids: set[str]) -> None:
    if message.get("role") != "tool" or message.get("tool_call_id") not in pending_ids:
        raise ValueError("工具返回未关联到待办调用")
    result = json.loads(message["content"])
    if set(result) != {"ok", "data", "error"} or type(result["ok"]) is not bool:
        raise ValueError("返回结构错误")
    if result["ok"]:
        if not isinstance(result["data"], dict) or result["error"] is not None:
            raise ValueError("成功返回必须有data且error为空")
    elif result["data"] is not None or not isinstance(result["error"], dict):
        raise ValueError("失败返回必须有error且data为空")
    if not result["ok"]:
        error = result["error"]
        if (
            set(error) != {"code", "message", "retryable"}
            or not isinstance(error["code"], str)
            or not error["code"]
            or not isinstance(error["message"], str)
            or type(error["retryable"]) is not bool
        ):
            raise ValueError("错误字段不符合返回契约")
    pending_ids.remove(message["tool_call_id"])
