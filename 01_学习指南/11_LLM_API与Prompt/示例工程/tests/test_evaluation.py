import pytest

from evaluation import EvaluationRecord, compare_prompt_versions, demo_records


def test_prompt_comparison_reports_format_task_latency_tokens_and_cost():
    report = compare_prompt_versions(
        demo_records(), input_price_per_million=2.0, output_price_per_million=8.0
    )

    assert set(report) == {"prompt_v1", "prompt_v2", "prompt_v3"}
    assert report["prompt_v1"]["format_success_rate"] == pytest.approx(2 / 3)
    assert report["prompt_v3"]["task_success_rate"] == 1.0
    assert report["prompt_v3"]["average_latency_ms"] > 0
    assert report["prompt_v3"]["input_tokens"] > 0
    assert report["prompt_v3"]["estimated_cost"] > 0


@pytest.mark.parametrize(
    "records, input_price, output_price, message",
    [([], 0, 0, "不能为空"), (demo_records(), -1, 0, "不能为负数")],
)
def test_invalid_evaluation_arguments_are_rejected(
    records, input_price, output_price, message
):
    with pytest.raises(ValueError, match=message):
        compare_prompt_versions(
            records,
            input_price_per_million=input_price,
            output_price_per_million=output_price,
        )


def test_negative_case_metrics_are_rejected():
    record = EvaluationRecord("v1", "c1", "refund", "{}", -1, 2, 20)

    with pytest.raises(ValueError, match="不能为负数"):
        compare_prompt_versions(
            [record], input_price_per_million=0, output_price_per_million=0
        )


def test_prompt_versions_must_use_the_same_unique_case_ids():
    records = [
        EvaluationRecord("v1", "case_1", "refund", "{}", 1, 1, 1),
        EvaluationRecord("v2", "case_2", "refund", "{}", 1, 1, 1),
    ]

    with pytest.raises(ValueError, match="同一组 case_id"):
        compare_prompt_versions(
            records, input_price_per_million=0, output_price_per_million=0
        )
