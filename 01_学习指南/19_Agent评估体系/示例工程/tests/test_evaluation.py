import json
from pathlib import Path

import pytest

from agents import run_agent
from dataset import build_cases, load_cases
from evaluate import build_report, evaluate
from metrics import aggregate, judge_agreement, paired_group_bootstrap, score_case

FIXTURE = Path(__file__).resolve().parents[1] / "fixtures" / "cases.json"


def test_dataset_has_sixty_unique_cases_and_disjoint_groups():
    cases = load_cases(FIXTURE)
    assert len(cases) == 60
    assert cases == build_cases()
    dev_groups = {case["group_id"] for case in cases if case["split"] == "dev"}
    test_groups = {case["group_id"] for case in cases if case["split"] == "test"}
    assert not dev_groups & test_groups
    assert all(not case["annotation"]["human_reviewed"] for case in cases)


def test_dataset_rejects_duplicate_and_cross_split(tmp_path):
    cases = build_cases()
    path = tmp_path / "cases.json"
    path.write_text(json.dumps([cases[0], cases[0]]), encoding="utf-8")
    with pytest.raises(ValueError, match="重复"):
        load_cases(path)
    cases[0]["split"] = "test"
    path.write_text(json.dumps(cases), encoding="utf-8")
    with pytest.raises(ValueError, match="同组"):
        load_cases(path)


@pytest.mark.parametrize(
    "scenario", ["lookup", "approval", "unknown", "timeout", "injection", "conflict"]
)
def test_guarded_meets_each_fixture_contract(scenario):
    case = next(case for case in build_cases() if case["scenario"] == scenario)
    output = run_agent(case["input"], "guarded")
    assert score_case(case, output)["task_success"]


def test_correct_answer_can_still_fail_due_to_unsafe_side_effect():
    case = next(case for case in build_cases() if case["scenario"] == "injection")
    scored = score_case(case, run_agent(case["input"], "baseline"))
    assert scored["answer_correct"] and scored["retrieval_hit"]
    assert not scored["safe"] and not scored["task_success"]


def test_report_denominators_cost_regressions_and_snapshot():
    report = build_report(FIXTURE)
    baseline = report["systems"]["baseline"]
    guarded = report["systems"]["guarded"]
    assert baseline["task_success"] == {"value": 1 / 3, "n": 30}
    assert guarded["task_success"] == {"value": 1.0, "n": 30}
    assert guarded["retrieval_hit"]["n"] == 10
    assert guarded["tool_selection"]["n"] == 30
    assert baseline["tool_calls_total"] == 35 and guarded["tool_calls_total"] == 20
    assert report["cost_delta_units"] == -45
    assert not report["regressions"] and report["gate"]["passed"]
    assert len(report["dataset_sha256"]) == 64


def test_empty_not_applicable_rate_and_bootstrap_pair_validation():
    with pytest.raises(ValueError, match="空"):
        aggregate([])
    cases = [case for case in build_cases() if case["scenario"] == "approval"]
    rows = evaluate(cases, "guarded")
    assert aggregate(rows)["answer_correct"] == {"value": None, "n": 0}
    with pytest.raises(ValueError, match="相同"):
        paired_group_bootstrap(rows, rows[:-1])
    with pytest.raises(ValueError, match="重复"):
        paired_group_bootstrap(rows + [rows[0]], rows)


def test_paired_group_bootstrap_reproducible_and_regression_negative():
    cases = build_cases()
    before, after = evaluate(cases, "baseline"), evaluate(cases, "guarded")
    assert paired_group_bootstrap(before, after) == paired_group_bootstrap(
        before, after
    )
    reversed_report = paired_group_bootstrap(after, before)
    assert reversed_report["high"] < 0


def test_judge_disputes_kappa_and_degenerate_labels():
    result = judge_agreement([True, False, True, False], [True, True, True, False])
    assert result["agreement"] == 0.75 and result["kappa"] == 0.5
    assert result["disputed_indices"] == [1]
    assert judge_agreement([True], [True])["kappa"] is None
    with pytest.raises(TypeError):
        judge_agreement([1], [True])
    with pytest.raises(ValueError):
        judge_agreement([], [])


def test_agent_input_does_not_receive_gold_or_mutate_environment():
    case = build_cases()[0]
    original = json.dumps(case["input"], sort_keys=True)
    run_agent(case["input"], "guarded")
    assert json.dumps(case["input"], sort_keys=True) == original
    assert "gold" not in case["input"]
    with pytest.raises(ValueError):
        run_agent(case["input"], "unknown")
