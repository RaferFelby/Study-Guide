"""顺序 Agent 控制器；动作校验和终止规则由控制器负责。"""

import json
from collections.abc import Callable
from copy import deepcopy
from dataclasses import asdict
from time import perf_counter

from state import TERMINAL_STATUSES, Action, AgentState, Status, ToolResult, transition
from tools import Tool


def action_key(action: Action) -> str:
    return json.dumps(
        {"tool": action.tool_name, "arguments": action.arguments},
        sort_keys=True,
        ensure_ascii=False,
    )


def approve_pending_action(state: AgentState) -> None:
    if state.status != Status.WAITING_CONFIRMATION or state.pending_action is None:
        raise ValueError("没有待确认动作")
    state.approved_action_key = action_key(state.pending_action)
    transition(
        state, Status.READY, "human_approved", action_key=state.approved_action_key
    )


def cancel_pending_action(state: AgentState) -> None:
    if state.status != Status.WAITING_CONFIRMATION:
        raise ValueError("当前没有待确认动作")
    transition(state, Status.CANCELLED, "human_declined")
    state.pending_action = None


def run_agent(
    state: AgentState,
    decide: Callable[[AgentState], Action],
    tools: dict[str, Tool],
    max_steps: int = 4,
    is_cancelled: Callable[[], bool] | None = None,
) -> AgentState:
    if max_steps < 1:
        raise ValueError("max_steps 必须大于 0")
    if state.status in TERMINAL_STATUSES or state.status == Status.WAITING_CONFIRMATION:
        return state
    if state.status != Status.READY:
        raise ValueError("只能从 ready 状态开始/继续")
    if not state.messages:
        state.messages.append({"role": "user", "content": state.task})
    while state.status not in TERMINAL_STATUSES:
        if is_cancelled is not None and is_cancelled():
            transition(state, Status.CANCELLED, "cancel_requested")
            return state
        if state.pending_action is None:
            if state.steps >= max_steps:
                transition(state, Status.STEP_LIMIT, "step_budget_exhausted")
                return state
            state.steps += 1
            transition(state, Status.DECIDING, "decision_started")
            started = perf_counter()
            # 传副本，防止决策器意外修改控制器状态/终止约束。
            try:
                action = decide(deepcopy(state))
            except (ValueError, TypeError, KeyError, RuntimeError) as error:
                transition(
                    state,
                    Status.FAILED,
                    "decision_failed",
                    error_type=type(error).__name__,
                )
                return state
            decision_ms = (perf_counter() - started) * 1000
            if not isinstance(action, Action) or action.kind not in {"tool", "final"}:
                transition(
                    state, Status.FAILED, "invalid_action", decision_ms=decision_ms
                )
                return state
            if is_cancelled is not None and is_cancelled():
                transition(state, Status.CANCELLED, "cancel_requested")
                return state
            if action.kind == "final":
                if (
                    not isinstance(action.final_text, str)
                    or not action.final_text.strip()
                ):
                    transition(state, Status.FAILED, "empty_final_answer")
                    return state
                state.final_text = action.final_text
                state.messages.append(
                    {"role": "assistant", "content": action.final_text}
                )
                transition(
                    state,
                    Status.COMPLETED,
                    "final_answer",
                    text=action.final_text,
                    decision_ms=decision_ms,
                )
                return state
            if not isinstance(action.arguments, dict) or action.tool_name not in tools:
                transition(state, Status.FAILED, "unknown_tool_or_invalid_arguments")
                return state
            try:
                key = action_key(action)
            except (TypeError, ValueError) as error:
                transition(
                    state,
                    Status.FAILED,
                    "non_json_arguments",
                    error_type=type(error).__name__,
                )
                return state
            if key in state.executed_actions:
                transition(
                    state, Status.LOOP_DETECTED, "repeated_action", action_key=key
                )
                return state
            state.pending_action = deepcopy(action)
            tool = tools[action.tool_name]
            if tool.requires_confirmation:
                transition(
                    state,
                    Status.WAITING_CONFIRMATION,
                    "confirmation_required",
                    action=asdict(action),
                    decision_ms=decision_ms,
                )
                return state
            transition(
                state,
                Status.WAITING_TOOL,
                "tool_started",
                action=asdict(action),
                decision_ms=decision_ms,
            )
        else:
            action = state.pending_action
            key = action_key(action)
            tool = tools.get(action.tool_name)
            if tool is None or state.approved_action_key != key:
                # 确认后参数变化或注册表变化不能沿用原批准。
                state.pending_action = None
                transition(state, Status.DECIDING, "invalid_pending_action")
                transition(state, Status.FAILED, "approval_mismatch")
                return state
            transition(
                state,
                Status.WAITING_TOOL,
                "approved_tool_started",
                action=asdict(action),
            )
        started = perf_counter()
        try:
            result = tool.execute(deepcopy(action.arguments))
        except (ValueError, TypeError, KeyError, RuntimeError, OSError) as error:
            transition(
                state,
                Status.FAILED,
                "tool_execution_failed",
                error_type=type(error).__name__,
            )
            return state
        if not isinstance(result, ToolResult) or not isinstance(result.data, dict):
            transition(state, Status.FAILED, "invalid_tool_result")
            return state
        elapsed_ms = (perf_counter() - started) * 1000
        observation = {
            "tool_name": action.tool_name,
            "arguments": deepcopy(action.arguments),
            "result": deepcopy(asdict(result)),
            "elapsed_ms": elapsed_ms,
        }
        state.tool_records.append(observation)
        state.messages.append({"role": "tool", "content": deepcopy(observation)})
        state.executed_actions.add(key)
        state.pending_action = None
        state.approved_action_key = None
        transition(state, Status.OBSERVING, "tool_observation", observation=observation)
        transition(state, Status.READY, "observation_recorded")
    return state
