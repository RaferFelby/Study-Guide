import pytest

from structured_output import (
    OutputValidationError,
    parse_and_validate,
    parse_json,
    validate_result_schema,
    validate_result_semantics,
)


def test_valid_json_passes_structure_and_semantics():
    result = parse_and_validate(
        '{"category":"refund","priority":2,"evidence":"申请退款"}',
        "我想申请退款",
    )

    assert result["category"] == "refund"


@pytest.mark.parametrize(
    "text, message",
    [
        ('```json\n{"category":"refund"}\n```', "无效 JSON"),
        ('{"category":"refund",}', "无效 JSON"),
        ('["refund"]', "必须是 JSON 对象"),
    ],
)
def test_invalid_json_is_reported(text, message):
    if text.startswith("["):
        with pytest.raises(OutputValidationError, match=message):
            validate_result_schema(parse_json(text))
    else:
        with pytest.raises(OutputValidationError, match=message):
            parse_json(text)


@pytest.mark.parametrize(
    "value, message",
    [
        ({"category": "refund", "priority": 2}, "缺少必需字段"),
        ({"category": "refund", "priority": True, "evidence": "退款"}, "整数"),
        ({"category": "unknown", "priority": 2, "evidence": "退款"}, "category"),
        ({"category": "refund", "priority": 4, "evidence": "退款"}, "整数"),
        (
            {"category": "refund", "priority": 2, "evidence": "退款", "extra": 1},
            "未定义字段",
        ),
    ],
)
def test_schema_rejects_wrong_fields_and_types(value, message):
    with pytest.raises(OutputValidationError, match=message):
        validate_result_schema(value)


def test_semantic_validation_rejects_evidence_not_in_source():
    value = {"category": "refund", "priority": 2, "evidence": "其他内容"}

    with pytest.raises(OutputValidationError, match="原文"):
        validate_result_semantics(value, "我申请退款")


def test_semantic_validation_rejects_category_mismatch():
    value = {"category": "refund", "priority": 2, "evidence": "电脑无法开机"}

    with pytest.raises(OutputValidationError, match="主题词不匹配"):
        validate_result_semantics(value, "电脑无法开机")
