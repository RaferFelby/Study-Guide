import math
import random

import pytest

from evaluation import compare
from sampling import evaluation_tasks, make_candidate, probabilities, sample_candidate
from selection import (
    inspect_candidate,
    majority_answer,
    outcome_score,
    process_scores,
    verified_score,
)
from strategies import DEFAULT_LIMITS, run_strategy


def task():
    return evaluation_tasks()[0]


def test_temperature_probabilities_sum_to_one_and_zero_is_argmax():
    logits = [2, 1, 0, -1, -2]
    cold = probabilities(logits, 0.5)
    warm = probabilities(logits, 2)
    assert math.isclose(sum(cold), 1) and math.isclose(sum(warm), 1)
    assert cold[0] > warm[0]
    assert probabilities(logits, 0) == [1, 0, 0, 0, 0]


@pytest.mark.parametrize("temperature", [-1, True, float("nan"), float("inf"), 6])
def test_invalid_temperature_is_rejected(temperature):
    with pytest.raises(ValueError):
        probabilities([2, 1, 0, -1, -2], temperature)


@pytest.mark.parametrize("logits", [None, [1], [1, 2, 3, 4, float("inf")]])
def test_invalid_candidate_scores_have_clear_error(logits):
    with pytest.raises(ValueError):
        probabilities(logits, 1)


def test_direct_sampler_validates_output_limit_and_candidate_type():
    with pytest.raises(ValueError):
        sample_candidate(task(), random.Random(17), maximum_output_bytes=True)
    with pytest.raises(ValueError):
        make_candidate(task(), "not-a-kind")


def test_same_seed_same_candidate_and_long_response_has_cost_but_no_answer():
    first = sample_candidate(task(), random.Random(17))
    assert first == sample_candidate(task(), random.Random(17))
    long_task = evaluation_tasks()[4]
    result = sample_candidate(long_task, random.Random(17))
    assert result["candidate"] is None and result["reason"] == "output_limit"
    assert result["output_bytes"] == 512


def test_vote_ties_abstain_and_repeated_wrong_answers_can_win():
    correct, wrong = make_candidate(task(), "correct"), make_candidate(task(), "wrong")
    assert majority_answer([correct, wrong]) is None
    assert majority_answer([wrong, wrong, correct]) == wrong["answer"]
    assert majority_answer([]) is None


def test_correct_final_answer_can_hide_wrong_steps():
    candidate = make_candidate(task(), "bad_steps")
    assert outcome_score(task(), candidate) == 1
    assert process_scores(task(), candidate) == [0, 1]
    assert verified_score(task(), candidate) == 0


def test_rule_verifier_accepts_good_trace_and_rejects_wrong_answer():
    assert verified_score(task(), make_candidate(task(), "correct")) == 1
    assert verified_score(task(), make_candidate(task(), "wrong")) == 0


def test_loop_and_step_limit_are_distinct_failures():
    assert inspect_candidate(make_candidate(task(), "loop"), 8) == "loop_detected"
    assert inspect_candidate(make_candidate(task(), "correct"), 1) == "step_limit"


def test_requested_count_and_candidate_budget_count_failed_attempts():
    limits = {**DEFAULT_LIMITS, "maximum_candidates": 2}
    result = run_strategy(evaluation_tasks()[3], "vote", 5, limits=limits)
    assert result["attempts"] == 2 and result["stop_reason"] == "candidate_budget"
    assert result["failures"] == ["loop_detected", "loop_detected"]
    assert result["answer"] is None and result["total_bytes"] > 0


def test_byte_reservation_prevents_new_generation_and_keeps_cost_bounded():
    limits = {**DEFAULT_LIMITS, "maximum_total_bytes": 100}
    result = run_strategy(task(), "vote", 5, limits=limits)
    assert result["attempts"] == 0 and result["total_bytes"] == 0
    assert result["stop_reason"] == "byte_budget"


def test_simulated_time_budget_stops_before_generation():
    limits = {**DEFAULT_LIMITS, "maximum_simulated_seconds": 0.001}
    result = run_strategy(task(), limits=limits)
    assert result["attempts"] == 0 and result["stop_reason"] == "simulated_time_budget"


def test_verification_budget_does_not_choose_unverified_candidate():
    fixture = {**task(), "logits": [10, -100, -100, -100, -100]}
    # generation reservation512+输入可容纳，但实际生成后剩余额不足验证。
    limits = {**DEFAULT_LIMITS, "maximum_output_bytes": 200, "maximum_total_bytes": 260}
    result = run_strategy(fixture, "best_of_n", 1, limits=limits)
    assert result["attempts"] == 1 and result["verifier_calls"] == 0
    assert result["stop_reason"] == "verification_budget" and result["answer"] is None


def test_actual_wall_clock_budget_late_candidate_is_discarded():
    times = iter([0.0, 0.0, 3.0, 3.0])
    result = run_strategy(task(), clock=lambda: next(times))
    assert result["stop_reason"] == "wall_time_budget" and result["attempts"] == 1
    assert result["answer"] is None and result["failures"] == ["late_candidate"]


@pytest.mark.parametrize(
    "key,value",
    [
        ("maximum_candidates", True),
        ("maximum_steps", 0),
        ("maximum_total_bytes", -1),
        ("maximum_seconds", float("inf")),
        ("maximum_simulated_seconds", 0),
    ],
)
def test_invalid_budget_values_are_rejected(key, value):
    with pytest.raises(ValueError):
        run_strategy(task(), limits={**DEFAULT_LIMITS, key: value})


def test_selection_refuses_reference_fields_and_all_wrong_candidates_abstain():
    with pytest.raises(ValueError):
        run_strategy({**task(), "reference": 5})
    result = run_strategy(evaluation_tasks()[2], "best_of_n", 5)
    assert result["attempts"] == 5 and result["verifier_calls"] == 5
    assert result["answer"] is None


def test_comparison_keeps_all_tasks_seeds_failures_and_unmeasured_llm_costs():
    report = compare()
    single, vote, best = report["summaries"]
    assert [item["n"] for item in report["summaries"]] == [18, 18, 18]
    assert [item["correct"] for item in report["summaries"]] == [5, 3, 6]
    assert [item["attempts"] for item in report["summaries"]] == [18, 90, 90]
    assert [item["answered"] for item in report["summaries"]] == [12, 12, 6]
    assert best["verifier_calls"] == 60
    assert single["total_bytes"] < vote["total_bytes"] < best["total_bytes"]
    assert all(
        item["llm_tokens"] is None and item["currency_cost"] is None
        for item in report["summaries"]
    )
    assert (
        report["unique_tasks"] == 6
        and report["real_llm_quality_cost_verified"] is False
    )
