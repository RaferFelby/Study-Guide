"""教学工具契约；校验器只支持本文件使用的扁平 Schema 子集。"""

import json
from dataclasses import dataclass, field

TOOL_SCHEMAS = {
    "search_policies": {
        "description": "查询当前身份可见的政策片段，返回原文与定位，不生成答案。",
        "parameters": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "minLength": 1,
                    "maxLength": 200,
                    "description": "英文服务/政策关键词，例如 storage retention",
                },
                "top_k": {
                    "type": "integer",
                    "minimum": 1,
                    "maximum": 5,
                    "description": "最多返回几个证据片段",
                },
            },
            "required": ["query", "top_k"],
            "additionalProperties": False,
        },
        "side_effect": "read_only",
    },
    "create_ticket": {
        "description": "在本进程内创建演示工单；需 staff 权限和该动作的明确批准。",
        "parameters": {
            "type": "object",
            "properties": {
                "title": {
                    "type": "string",
                    "minLength": 1,
                    "maxLength": 80,
                    "description": "工单标题，不含秘密",
                },
                "idempotency_key": {
                    "type": "string",
                    "minLength": 1,
                    "maxLength": 100,
                    "description": "同一业务请求保持相同键，不能用于不同标题",
                },
            },
            "required": ["title", "idempotency_key"],
            "additionalProperties": False,
        },
        "side_effect": "local_write",
    },
}


@dataclass(frozen=True)
class ToolCall:
    call_id: str
    name: str
    arguments_json: str


@dataclass(frozen=True)
class ToolContext:
    actor_id: str
    role: str
    approved_fingerprints: frozenset[str] = field(default_factory=frozenset)


def reject_duplicate_keys(pairs: list[tuple[str, object]]) -> dict:
    result = {}
    for name, value in pairs:
        if name in result:
            raise ValueError(f"JSON 键重复：{name}")
        result[name] = value
    return result


def reject_nonfinite_constant(value: str) -> None:
    raise ValueError(f"JSON 非法数值：{value}")


def parse_arguments(text: str) -> dict:
    if not isinstance(text, str):
        raise TypeError("arguments_json 必须是字符串")
    if len(text.encode("utf-8")) > 8192:
        raise ValueError("参数JSON超过8192字节")
    arguments = json.loads(
        text,
        object_pairs_hook=reject_duplicate_keys,
        parse_constant=reject_nonfinite_constant,
    )
    if not isinstance(arguments, dict):
        raise TypeError("参数必须是JSON对象")
    return arguments


def validate_arguments(arguments: dict, schema: dict) -> None:
    properties = schema["properties"]
    missing = set(schema["required"]) - set(arguments)
    extra = set(arguments) - set(properties)
    if missing:
        raise ValueError(f"缺少参数：{sorted(missing)}")
    if extra:
        raise ValueError(f"不允许额外参数：{sorted(extra)}")
    for name, value in arguments.items():
        rule = properties[name]
        if rule["type"] == "string":
            if not isinstance(value, str) or not value.strip():
                raise ValueError(f"{name} 必须是非空字符串")
            if (
                not rule.get("minLength", 0)
                <= len(value)
                <= rule.get("maxLength", len(value))
            ):
                raise ValueError(f"{name} 长度越界")
        elif rule["type"] == "integer":
            if type(value) is not int:
                raise ValueError(f"{name} 必须是整数，不能是布尔值/字符串")
            if not rule.get("minimum", value) <= value <= rule.get("maximum", value):
                raise ValueError(f"{name} 数值越界")
        else:
            raise ValueError("教学校验器不支持该Schema类型")


def success(data: dict) -> dict:
    return {"ok": True, "data": data, "error": None}


def failure(code: str, message: str, retryable: bool = False) -> dict:
    return {
        "ok": False,
        "data": None,
        "error": {"code": code, "message": message, "retryable": retryable},
    }
