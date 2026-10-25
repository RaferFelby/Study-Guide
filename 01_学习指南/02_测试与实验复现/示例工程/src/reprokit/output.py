import json
from typing import Any


class InvalidToolResponse(ValueError):
    """工具返回的文本不是预期结构。"""


def parse_tool_response(text: str) -> str:
    """解析 {"answer": "..."}，并拒绝坏 JSON 或错误类型。"""
    try:
        value: Any = json.loads(text)
    except json.JSONDecodeError as exc:
        raise InvalidToolResponse("工具返回的内容不是 JSON") from exc
    if not isinstance(value, dict) or not isinstance(value.get("answer"), str):
        raise InvalidToolResponse("工具响应缺少字符串 answer")
    return value["answer"]
