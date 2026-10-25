"""在固定数据集上比较 Prompt 结果，并报告格式、任务、延迟和示例成本。"""

from collections import defaultdict
from dataclasses import dataclass

from structured_output import OutputValidationError, parse_json, validate_result_schema


@dataclass(frozen=True)
class EvaluationRecord:
    prompt_version: str
    case_id: str
    expected_category: str
    output_text: str
    input_tokens: int
    output_tokens: int
    latency_ms: float


def compare_prompt_versions(
    records: list[EvaluationRecord],
    *,
    input_price_per_million: float,
    output_price_per_million: float,
) -> dict[str, dict[str, float]]:
    """按 prompt 版本汇总格式率、正确率、平均延迟、token 数和估算成本。"""
    if not records:
        raise ValueError("records 不能为空")
    if input_price_per_million < 0 or output_price_per_million < 0:
        raise ValueError("示例价格不能为负数")

    groups: dict[str, list[EvaluationRecord]] = defaultdict(list)
    for record in records:
        if record.input_tokens < 0 or record.output_tokens < 0 or record.latency_ms < 0:
            raise ValueError("token 数和 latency_ms 不能为负数")
        groups[record.prompt_version].append(record)

    case_sets: list[set[str]] = []
    for group in groups.values():
        case_ids = [record.case_id for record in group]
        if len(case_ids) != len(set(case_ids)):
            raise ValueError("同一个 Prompt 版本中不能有重复 case_id")
        case_sets.append(set(case_ids))
    if any(case_ids != case_sets[0] for case_ids in case_sets[1:]):
        raise ValueError("所有 Prompt 版本必须评估同一组 case_id")

    report: dict[str, dict[str, float]] = {}
    for prompt_version, group in groups.items():
        valid_count = 0
        correct_count = 0
        for record in group:
            try:
                result = validate_result_schema(parse_json(record.output_text))
            except OutputValidationError:
                continue
            valid_count += 1
            if result["category"] == record.expected_category:
                correct_count += 1

        input_tokens = sum(record.input_tokens for record in group)
        output_tokens = sum(record.output_tokens for record in group)
        estimated_cost = (
            input_tokens * input_price_per_million
            + output_tokens * output_price_per_million
        ) / 1_000_000
        report[prompt_version] = {
            "format_success_rate": valid_count / len(group),
            "task_success_rate": correct_count / len(group),
            "average_latency_ms": sum(record.latency_ms for record in group)
            / len(group),
            "input_tokens": float(input_tokens),
            "output_tokens": float(output_tokens),
            "estimated_cost": estimated_cost,
        }
    return report


def demo_records() -> list[EvaluationRecord]:
    """返回小型固定夹具，验证统计逻辑；不是模型实测数据。"""
    expected = ["refund", "technical", "other"]
    variants: dict[str, list[str]] = {
        "prompt_v1": [
            '{"category":"refund","priority":2,"evidence":"退款"}',
            "category=technical",
            '{"category":"other","priority":2,"evidence":"联系"}',
        ],
        "prompt_v2": [
            '{"category":"refund","priority":2,"evidence":"退款"}',
            '{"category":"technical","priority":1,"evidence":"登录"}',
            '{"category":"refund","priority":2,"evidence":"联系"}',
        ],
        "prompt_v3": [
            '{"category":"refund","priority":2,"evidence":"退款"}',
            '{"category":"technical","priority":1,"evidence":"登录"}',
            '{"category":"other","priority":2,"evidence":"联系"}',
        ],
    }

    records = []
    input_token_overhead = {"prompt_v1": 0, "prompt_v2": 8, "prompt_v3": 15}
    output_token_overhead = {"prompt_v1": 0, "prompt_v2": 1, "prompt_v3": 3}
    latency_overhead_ms = {"prompt_v1": 0, "prompt_v2": 15, "prompt_v3": 30}
    for prompt_version, outputs in variants.items():
        for index, output_text in enumerate(outputs):
            records.append(
                EvaluationRecord(
                    prompt_version=prompt_version,
                    case_id=f"case_{index + 1}",
                    expected_category=expected[index],
                    output_text=output_text,
                    input_tokens=90 + index * 10 + input_token_overhead[prompt_version],
                    output_tokens=12
                    + index * 2
                    + output_token_overhead[prompt_version],
                    latency_ms=120 + index * 25 + latency_overhead_ms[prompt_version],
                )
            )
    return records
