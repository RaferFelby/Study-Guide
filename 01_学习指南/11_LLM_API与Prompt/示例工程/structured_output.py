"""用标准库检查 JSON 结构，再检查业务语义。"""

from json import JSONDecodeError, loads
from typing import Any

RESULT_SCHEMA = {
    "type": "object",
    "required": ["category", "priority", "evidence"],
    "additionalProperties": False,
    "properties": {
        "category": {"type": "string", "enum": ["refund", "technical", "other"]},
        "priority": {"type": "integer", "minimum": 1, "maximum": 3},
        "evidence": {"type": "string", "minLength": 1},
    },
}


class OutputValidationError(ValueError):
    """模型返回的文本无法按本示例的数据契约安全使用。"""


def parse_json(text: str) -> Any:
    """只解析 JSON；多余说明文字、代码围栏和非法逗号会解析失败。"""
    try:
        return loads(text)
    except JSONDecodeError as error:
        raise OutputValidationError(
            f"无效 JSON：第 {error.lineno} 行，第 {error.colno} 列：{error.msg}"
        ) from error


def validate_result_schema(value: Any) -> dict[str, Any]:
    """验证本课程所需 schema 子集，不宣称是完整 JSON Schema 实现。"""
    if not isinstance(value, dict):
        raise OutputValidationError("结果必须是 JSON 对象")

    required_fields = RESULT_SCHEMA["required"]
    missing_fields = [field for field in required_fields if field not in value]
    if missing_fields:
        raise OutputValidationError(f"缺少必需字段：{', '.join(missing_fields)}")

    extra_fields = set(value) - set(RESULT_SCHEMA["properties"])
    if extra_fields:
        raise OutputValidationError(
            f"出现未定义字段：{', '.join(sorted(extra_fields))}"
        )

    category = value["category"]
    if not isinstance(category, str) or category not in {
        "refund",
        "technical",
        "other",
    }:
        raise OutputValidationError("category 必须是 refund、technical 或 other")

    priority = value["priority"]
    if (
        isinstance(priority, bool)
        or not isinstance(priority, int)
        or not 1 <= priority <= 3
    ):
        raise OutputValidationError("priority 必须是 1 到 3 的整数")

    evidence = value["evidence"]
    if not isinstance(evidence, str) or not evidence.strip():
        raise OutputValidationError("evidence 必须是非空字符串")
    return value


def validate_result_semantics(value: dict[str, Any], source_text: str) -> None:
    """检查字段之间的业务含义；结构正确不等于分类正确。"""
    evidence = value["evidence"]
    if evidence not in source_text:
        raise OutputValidationError("evidence 必须是用户原文中的连续片段")

    category_keywords = {
        "refund": ("退款", "退货", "refund"),
        "technical": ("报错", "无法登录", "error", "login"),
        "other": (),
    }
    keywords = category_keywords[value["category"]]
    if keywords and not any(keyword in source_text.lower() for keyword in keywords):
        raise OutputValidationError("category 与用户原文中的主题词不匹配")


def parse_and_validate(text: str, source_text: str) -> dict[str, Any]:
    """按 JSON 解析、结构验证、语义验证的顺序返回结果。"""
    value = parse_json(text)
    result = validate_result_schema(value)
    validate_result_semantics(result, source_text)
    return result
