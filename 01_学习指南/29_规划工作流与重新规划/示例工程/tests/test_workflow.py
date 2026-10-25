import copy
import threading

import pytest

import workflow
from demo import compare_strategies, demonstrate_resume, load_scenarios
from workflow import (
    load_checkpoint,
    make_plan,
    run_workflow,
    save_checkpoint,
    validate_plan,
)


def scenario(identifier):
    return copy.deepcopy(
        next(item for item in load_scenarios() if item["id"] == identifier)
    )


@pytest.mark.parametrize("strategy", ["fixed", "react_policy", "plan_execute"])
def test_normal_task_has_sources_and_four_attempts(strategy):
    state = run_workflow(strategy, scenario("normal"))
    assert state["status"] == "completed" and state["attempts"] == 4
    assert len(state["completed"]["draft"]["sources"]) == 2
    assert state["completed"]["review"]["passed"]


def test_dependency_nodes_are_dispatched_in_same_wave():
    state = run_workflow("plan_execute", scenario("normal"))
    waves = [event["nodes"] for event in state["trace"] if event["event"] == "dispatch"]
    assert waves == [["policy", "ticket"], ["draft"], ["review"]]


def test_independent_tools_actually_overlap(monkeypatch):
    original = workflow.execute_tool
    barrier = threading.Barrier(2, timeout=2)

    def execute(name, inputs, fixture):
        if name in {"load_policy", "load_ticket"}:
            barrier.wait()
        return original(name, inputs, fixture)

    monkeypatch.setattr(workflow, "execute_tool", execute)
    assert run_workflow("plan_execute", scenario("normal"))["status"] == "completed"


@pytest.mark.parametrize("identifier", ["primary_down", "primary_stale"])
def test_plan_repair_reuses_ticket_and_keeps_failure_record(identifier):
    state = run_workflow("plan_execute", scenario(identifier))
    assert state["status"] == "completed" and state["attempts"] == 5
    assert state["replans"] == 1 and "policy" in state["errors"]
    repairs = [event for event in state["trace"] if event["event"] == "repair"]
    assert repairs[0]["reused"] == ["ticket"]
    assert "simulated-approved-backup/v1" in state["completed"]["draft"]["sources"]


def test_fixed_stops_and_reactive_runs_one_action_per_observation():
    assert run_workflow("fixed", scenario("primary_down"))["status"] == "needs_human"
    reactive = run_workflow("react_policy", scenario("primary_down"))
    assert reactive["status"] == "completed"
    assert all(
        len(event["nodes"]) == 1
        for event in reactive["trace"]
        if event["event"] == "dispatch"
    )


def test_backup_failure_has_only_one_repair_and_stops():
    state = run_workflow("plan_execute", scenario("both_down"))
    assert state["status"] == "needs_human" and state["replans"] == 1
    assert state["attempts"] == 3 and "draft" not in state["completed"]


def test_disallowed_backup_and_zero_repair_budget_are_respected():
    fixture = scenario("primary_down")
    fixture["allow_backup"] = False
    assert run_workflow("plan_execute", fixture)["attempts"] == 2
    state = run_workflow("plan_execute", scenario("primary_down"), maximum_replans=0)
    assert state["status"] == "needs_human" and state["replans"] == 0


def test_attempt_budget_counts_failed_tools_too():
    state = run_workflow("plan_execute", scenario("primary_down"), maximum_attempts=4)
    assert state["status"] == "budget_exhausted" and state["attempts"] == 4
    assert "draft" in state["completed"] and "review" not in state["completed"]


def test_review_failure_blocks_publication_even_simulated_approval():
    fixture = scenario("publish_gate")
    fixture["review_passed"] = False
    state = run_workflow("plan_execute", fixture, simulated_approval=True)
    assert state["status"] == "needs_human" and "publish" not in state["completed"]


def test_approval_gate_checkpoint_and_resume_do_not_repeat_read_tools(tmp_path):
    fixture = scenario("publish_gate")
    path = tmp_path / "state.json"
    waiting = run_workflow("plan_execute", fixture, checkpoint_path=path)
    assert waiting["status"] == "awaiting_approval" and waiting["attempts"] == 4
    assert "publish" not in waiting["completed"]
    state = load_checkpoint(path, "plan_execute", fixture)
    resumed = run_workflow(
        "plan_execute",
        fixture,
        state=state,
        simulated_approval=True,
        checkpoint_path=path,
    )
    assert resumed["status"] == "completed" and resumed["attempts"] == 5
    assert (
        resumed["completed"]["publish"]["status"] == "simulated_only_no_external_send"
    )


def test_checkpoint_rejects_mismatched_strategy_and_scenario(tmp_path):
    path = tmp_path / "state.json"
    fixture = scenario("normal")
    save_checkpoint(path, run_workflow("fixed", fixture))
    with pytest.raises(ValueError, match="不匹配"):
        load_checkpoint(path, "plan_execute", fixture)
    with pytest.raises(ValueError, match="不匹配"):
        load_checkpoint(path, "fixed", scenario("bad_ticket"))
    with pytest.raises(ValueError, match="恢复预算"):
        run_workflow(
            "fixed",
            fixture,
            state=load_checkpoint(path, "fixed", fixture),
            maximum_attempts=20,
        )


@pytest.mark.parametrize(
    "mutation",
    ["cycle", "missing", "duplicate", "unknown_tool", "no_gate", "no_review"],
)
def test_invalid_plans_are_rejected(mutation):
    plan = make_plan(True)
    if mutation == "cycle":
        plan[0]["needs"] = ["review"]
    elif mutation == "missing":
        plan[2]["needs"] = ["missing"]
    elif mutation == "duplicate":
        plan.append(plan[0])
    elif mutation == "unknown_tool":
        plan[0]["tool"] = "shell"
    elif mutation == "no_gate":
        plan[-1]["approval"] = False
    else:
        plan[-1]["needs"] = ["draft"]
    with pytest.raises(ValueError):
        validate_plan(plan)


def test_six_case_comparison_and_simulation_scope():
    report = compare_strategies()
    assert [item["completed"] for item in report["strategies"]] == [1, 3, 3]
    assert [item["tool_attempts"] for item in report["strategies"]] == [16, 22, 23]
    assert all(
        item["n"] == 6 and item["llm_calls"] == 0 and item["currency_cost"] is None
        for item in report["strategies"]
    )
    assert demonstrate_resume()["approval_origin"].startswith("simulated")
