from dataclasses import replace

import pytest

from agent import approve_pending_action, cancel_pending_action, run_agent
from policy import policy_lookup, policy_repeat, policy_ticket
from state import Action, AgentState, Status, ToolResult, transition
from tools import Tool, make_tools


def test_lookup_observation_then_final():
    state = AgentState("查询", "test")
    run_agent(state, policy_lookup, make_tools([]))
    assert state.status == Status.COMPLETED
    assert state.steps == 2
    assert "30 days" in state.final_text
    assert len(state.tool_records) == 1
    assert state.tool_records[0]["elapsed_ms"] >= 0
    assert state.messages[0]["role"] == "user"
    assert state.trace[-1]["to"] == "completed"


def test_repeat_is_detected_before_second_execution():
    state = AgentState("重复", "test")
    run_agent(state, policy_repeat, make_tools([]))
    assert state.status == Status.LOOP_DETECTED
    assert len(state.tool_records) == 1


def test_max_steps_is_decision_budget_not_tool_budget():
    state = AgentState("预算", "test")
    run_agent(state, policy_lookup, make_tools([]), max_steps=1)
    assert state.status == Status.STEP_LIMIT
    assert len(state.tool_records) == 1
    assert state.final_text is None


def test_cancel_before_start_has_no_tool_effect():
    state = AgentState("取消", "test")
    store = []
    run_agent(state, policy_ticket, make_tools(store), is_cancelled=lambda: True)
    assert state.status == Status.CANCELLED
    assert store == []


def test_cancel_after_decision_before_execution():
    signals = iter([False, True])
    state = AgentState("取消", "test")
    run_agent(state, policy_lookup, make_tools([]), is_cancelled=lambda: next(signals))
    assert state.status == Status.CANCELLED
    assert state.tool_records == []


def test_confirmation_wait_approve_resume_executes_once():
    state = AgentState("工单", "test")
    store = []
    tools = make_tools(store)
    run_agent(state, policy_ticket, tools)
    assert state.status == Status.WAITING_CONFIRMATION
    assert store == []
    run_agent(state, policy_ticket, tools)
    assert store == []
    approve_pending_action(state)
    run_agent(state, policy_ticket, tools)
    assert state.status == Status.COMPLETED
    assert len(store) == 1
    assert state.steps == 2
    run_agent(state, policy_ticket, tools)
    assert len(store) == 1


def test_decline_is_terminal_without_write():
    state = AgentState("工单", "test")
    store = []
    run_agent(state, policy_ticket, make_tools(store))
    cancel_pending_action(state)
    assert state.status == Status.CANCELLED
    assert store == []


def test_changed_arguments_invalidate_approval():
    state = AgentState("工单", "test")
    store = []
    tools = make_tools(store)
    run_agent(state, policy_ticket, tools)
    approve_pending_action(state)
    state.pending_action = replace(state.pending_action, arguments={"title": "changed"})
    run_agent(state, policy_ticket, tools)
    assert state.status == Status.FAILED
    assert store == []


@pytest.mark.parametrize(
    "action", [Action("bad"), Action("tool", "unknown"), Action("final")]
)
def test_invalid_decision_is_failed(action):
    state = AgentState("错误", "test")
    run_agent(state, lambda state: action, make_tools([]))
    assert state.status == Status.FAILED


def test_structured_tool_failure_can_be_observed_and_reported():
    state = AgentState("查未知", "test")

    def decide(state):
        if not state.tool_records:
            return Action("tool", "lookup_policy", {"service": "unknown"})
        return Action("final", final_text="未找到，无法回答")

    run_agent(state, decide, make_tools([]))
    assert state.status == Status.COMPLETED
    assert state.tool_records[0]["result"]["error_code"] == "not_found"


def test_tool_exception_marks_failed_and_preserves_trace():
    def fail(arguments):
        raise OSError("模拟失败")

    state = AgentState("工具异常", "test")
    run_agent(state, lambda state: Action("tool", "broken"), {"broken": Tool(fail)})
    assert state.status == Status.FAILED
    assert state.trace[-1]["error_type"] == "OSError"


def test_policy_receives_copy_and_cannot_change_controller_budget():
    state = AgentState("副本", "test")

    def decide(copy):
        copy.steps = -100
        return Action("tool", "lookup_policy", {"service": "storage"})

    run_agent(state, decide, make_tools([]), max_steps=1)
    assert state.status == Status.STEP_LIMIT
    assert state.steps == 1


def test_illegal_transition_and_invalid_budget_fail():
    state = AgentState("错误", "test")
    with pytest.raises(ValueError):
        transition(state, Status.COMPLETED, "skip")
    with pytest.raises(ValueError):
        run_agent(state, policy_lookup, make_tools([]), max_steps=0)


def test_non_json_arguments_do_not_execute():
    state = AgentState("参数", "test")
    run_agent(
        state,
        lambda state: Action("tool", "lookup_policy", {"service": {"set"}}),
        make_tools([]),
    )
    assert state.status == Status.FAILED
    assert not state.tool_records


def test_invalid_tool_return_is_failed():
    state = AgentState("协议", "test")
    run_agent(
        state,
        lambda state: Action("tool", "broken"),
        {"broken": Tool(lambda arguments: None)},
    )
    assert state.status == Status.FAILED


def test_tool_result_error_does_not_mean_controller_crashed():
    result = ToolResult(False, error_code="not_found")
    assert not result.ok
    assert result.data == {}
