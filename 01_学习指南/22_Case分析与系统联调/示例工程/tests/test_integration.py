import json
from dataclasses import replace

import pytest

from cases import make_cases
from contracts import Settings
from experiments import compare, evaluate, run_experiments
from parsing import parse_model_output
from pipeline import run_pipeline


def test_five_failure_roots_and_three_regressions_are_explicit():
    cases = make_cases()
    assert len(cases) == 8 and len({case["case_id"] for case in cases}) == 8
    failures = [case for case in cases if case["annotation"]["root_cause"]]
    assert len(failures) == 5
    assert {case["annotation"]["root_cause"] for case in failures} == {
        "retrieval",
        "tool_contract",
        "parsing",
        "authorization",
        "upstream",
    }
    assert all(
        not case["annotation"]["reviewed_by_independent_human"] for case in cases
    )


@pytest.mark.parametrize(
    "name, expected",
    [
        ("fix_retrieval", "retrieval-alias"),
        ("fix_arguments", "tool-arguments"),
        ("fix_parser", "parse-fence"),
        ("fix_permissions", "permission-cross-user"),
        ("fix_retry", "upstream-transient"),
    ],
)
def test_each_single_variable_fixes_exactly_one_case(name, expected):
    report = run_experiments()
    assert report["reports"]["baseline"]["successes"] == 3
    assert report["reports"][name]["successes"] == 4
    assert report["comparisons"][name]["improved"] == [expected]
    assert report["comparisons"][name]["regressed"] == []
    before, after = (
        report["reports"]["baseline"]["settings"],
        report["reports"][name]["settings"],
    )
    assert sum(before[key] != after[key] for key in before) == 1


def test_combined_eight_of_eight_without_regressions():
    report = run_experiments()
    assert report["reports"]["combined"]["successes"] == 8
    assert report["comparisons"]["combined"]["regressed"] == []
    assert report["comparisons"]["combined"]["attempt_delta"] == 2
    assert len(report["case_sha256"]) == 64


def test_owner_check_happens_before_read_and_permissions_not_retried():
    case = next(
        case for case in make_cases() if case["case_id"] == "permission-cross-user"
    )
    result = run_pipeline(case["input"], Settings(enforce_owner=True, max_attempts=2))
    assert result["actual_reads"] == 0 and result["tool_attempts"] == 1
    assert result["output"]["status"] == "refused"
    assert not any(event["stage"] == "model" for event in result["events"])


def test_retry_budget_and_contract_errors_do_not_retry():
    cases = make_cases()
    transient = next(case for case in cases if case["case_id"] == "upstream-transient")
    fixed = run_pipeline(transient["input"], Settings(max_attempts=2))
    assert fixed["tool_attempts"] == 2 and fixed["actual_reads"] == 1
    persistent = {**transient["input"], "transient_failures": 3}
    failed = run_pipeline(persistent, Settings(max_attempts=2))
    assert failed["output"]["status"] == "failed" and failed["tool_attempts"] == 2
    contract = next(case for case in cases if case["case_id"] == "tool-arguments")
    assert (
        run_pipeline(contract["input"], Settings(max_attempts=2))["tool_attempts"] == 1
    )


def test_parser_exact_fence_and_schema_not_arbitrary_repair():
    wrapped = '```json\n{"status":"answered","days":30}\n```'
    with pytest.raises(ValueError):
        parse_model_output(wrapped)
    assert parse_model_output(wrapped, True)["days"] == 30
    for text in [
        "prefix " + wrapped,
        '{"status":"answered","days":true}',
        '{"status":"answered","days":30,"owner":"bob"}',
    ]:
        with pytest.raises(ValueError):
            parse_model_output(text, True)


def test_failure_propagation_and_trace_identity():
    case = next(case for case in make_cases() if case["case_id"] == "retrieval-alias")
    result = run_pipeline(case["input"], Settings())
    assert [event["stage"] for event in result["events"]] == ["retrieval", "task"]
    assert result["tool_attempts"] == 0
    assert all(event["trace_id"] == result["trace_id"] for event in result["events"])
    assert result["duration_ms_measured"] >= 0


def test_compare_ids_and_unknown_not_guessed():
    before = evaluate(Settings())
    after = evaluate(replace(Settings(), use_aliases=True))
    after["rows"].pop()
    with pytest.raises(ValueError):
        compare(before, after)
    unknown = make_cases()[-1]
    assert (
        run_pipeline(unknown["input"], Settings(True, True, True, True, 2))["output"]
        == unknown["gold"]
    )
    assert "gold" not in unknown["input"]
    json.dumps(run_experiments())


def test_attempts_config_rejects_unbounded_retry():
    for value in (0, 3, True, 1.5):
        with pytest.raises(ValueError):
            Settings(max_attempts=value)
