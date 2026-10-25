"""固定数据、抽取失败、分母与统计假设的正常和边界检查。"""

import copy
import json
import shutil

import pytest

from comparison import FIELDS, compare_configs
from experiment import evaluate_records
from metrics import estimate_pass_at_k, paired_bootstrap, wilson_interval
from scoring import extract_choice, extract_number, grade_numeric
from suite import FIXTURES, build_prompt, load_snapshot


@pytest.mark.parametrize(
    "text,expected",
    [
        ("#### 12", "12"),
        ("过程 99\nA: 12", "12"),
        ("#### 1,234.50", "1234.50"),
        ("#### -2", "-2"),
        ("#### +2.0", "2.0"),
    ],
)
def test_number_uses_only_final_declared_answer(text, expected):
    assert str(extract_number(text)) == expected


@pytest.mark.parametrize(
    "text",
    [
        "",
        "答案是12",
        "A: 1 or 2",
        "#### NaN",
        "#### 1,23",
        "#### 12\nextra",
        "A: 12 dollars",
    ],
)
def test_unsupported_numeric_format_is_not_guessed(text):
    assert extract_number(text) is None


def test_numeric_decimal_equivalence():
    assert grade_numeric("#### 12.0", "A: 12")["correct"]
    assert not grade_numeric("A: 13", "#### 12")["correct"]
    with pytest.raises(ValueError, match="参考"):
        grade_numeric("#### 12", "bad reference")


@pytest.mark.parametrize(
    "text,expected",
    [
        ("A", "A"),
        ("解释\n答案：D", "D"),
        ("A or B", None),
        ("Because A is mentioned", None),
        ("答案：E", None),
    ],
)
def test_choice_extraction_is_explicit(text, expected):
    assert extract_choice(text) == expected


def test_failed_extraction_stays_in_denominator():
    records = [
        {"ground_truth": "#### 12", "demo": {"solution": text, "is_correct": correct}}
        for text, correct in [("A: 12", True), ("12", False)]
    ]
    report = evaluate_records(records, "demo")
    assert report["n"] == 2 and report["correct"] == report["format_failures"] == 1
    assert report["accuracy"] == 0.5


def test_empty_evaluation_is_not_zero_accuracy():
    with pytest.raises(ValueError, match="不能为空"):
        evaluate_records([], "demo")


def test_upstream_disagreement_is_visible():
    result = evaluate_records(
        [
            {
                "ground_truth": "#### 12",
                "demo": {"solution": "A: 12", "is_correct": False},
            }
        ],
        "demo",
    )
    assert result["label_disagreements"] == ["gsm8k-archive-0000"]


def test_real_snapshot_and_train_demos():
    records, demos, manifest = load_snapshot()
    assert len(records) == 1319 and len(demos) == 5
    assert manifest["commit"] == "3101c7d5072418e28b9008a6636bde82a006892c"
    assert {row["question"] for row in demos}.isdisjoint(
        {row["question"] for row in records}
    )


def test_snapshot_mutation_rejected(tmp_path):
    for path in FIXTURES.iterdir():
        shutil.copyfile(path, tmp_path / path.name)
    path = tmp_path / "demos.json"
    path.write_text("[]", encoding="utf-8")
    with pytest.raises(ValueError, match="哈希"):
        load_snapshot(tmp_path)


def test_prompt_does_not_copy_target_reference():
    record = {"question": "独立问题", "ground_truth": "SECRET_REFERENCE"}
    demo = {"question": "训练例", "answer": "#### 2"}
    zero, one = build_prompt(record, [demo], 0), build_prompt(record, [demo], 1)
    assert "SECRET_REFERENCE" not in zero + one
    assert "训练例" not in zero and "训练例" in one
    assert zero.endswith("Question: 独立问题\nAnswer:")


def test_prompt_rejects_self_demo_and_bad_shots():
    task = {"question": "same", "ground_truth": "#### 1"}
    demos = [{"question": "same", "answer": "#### 1"}]
    with pytest.raises(ValueError, match="待评题"):
        build_prompt(task, demos, 1)
    for shots in (-1, 2, True):
        with pytest.raises(ValueError):
            build_prompt(task, demos, shots)


def test_wilson_is_not_zero_width_at_extremes():
    assert wilson_interval(0, 12)[1] == pytest.approx(0.24249400665524085)
    assert wilson_interval(12, 12)[0] == pytest.approx(0.7575059933447591)
    assert wilson_interval(6, 12)[0] < 0.5 < wilson_interval(6, 12)[1]


@pytest.mark.parametrize("correct,total", [(0, 0), (-1, 10), (11, 10), (True, 10)])
def test_invalid_counts_fail(correct, total):
    with pytest.raises(ValueError):
        wilson_interval(correct, total)


def test_paired_bootstrap_preserves_task_pair():
    before, after = [False, True, False, True], [True, True, False, True]
    result = paired_bootstrap(before, after, 100, 7)
    assert result == paired_bootstrap(before, after, 100, 7)
    assert result["mean_difference"] == 0.25
    assert result["resampling_unit"] == "aligned_question"
    assert before == [False, True, False, True]
    with pytest.raises(ValueError):
        paired_bootstrap(before, after[:2])


def test_pass_at_k_and_invalid_k():
    assert estimate_pass_at_k(10, 2, 1) == pytest.approx(0.2)
    assert estimate_pass_at_k(10, 2, 3) == pytest.approx(1 - 56 / 120)
    assert estimate_pass_at_k(10, 0, 3) == 0
    assert estimate_pass_at_k(10, 9, 3) == 1
    with pytest.raises(ValueError):
        estimate_pass_at_k(1, 1, 10)


def test_comparison_marks_unknown_as_not_comparable():
    config = {field: "fixed" for field in FIELDS}
    assert compare_configs(config, copy.deepcopy(config))["directly_comparable"]
    other = dict(config, shots=None, quantization="int4")
    result = compare_configs(config, other)
    assert not result["directly_comparable"]
    statuses = {row["field"]: row["status"] for row in result["differences"]}
    assert statuses["shots"] == "unknown" and statuses["quantization"] == "different"


def test_all_public_archived_labels_recomputed_without_using_labels():
    records, _, _ = load_snapshot()
    for name, expected in (("6b_finetuning", 286), ("6b_verification", 515)):
        result = evaluate_records(records, name)
        assert result["correct"] == expected and result["label_disagreements"] == []
    changed = copy.deepcopy(records[:1])
    changed[0]["6b_finetuning"]["is_correct"] = True
    assert not evaluate_records(changed, "6b_finetuning")["details"][0]["correct"]


def test_manifest_is_json_and_license_preserved():
    manifest = json.loads((FIXTURES / "manifest.json").read_text(encoding="utf-8"))
    assert "GSM8K-LICENSE.txt" in manifest["sources"]
    assert "Copyright (c) 2021 OpenAI" in (FIXTURES / "GSM8K-LICENSE.txt").read_text(
        encoding="utf-8"
    )
