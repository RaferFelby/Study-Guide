"""可逐步执行的 harness；一个数据库同一时刻只允许一个操作者。"""

from pathlib import Path

from contracts import (
    POLICY,
    action_key,
    build_context,
    evaluate_final,
    has_evidence,
    validate_action,
)
from storage import commit, connect, load, save


def fail(path: Path, state: dict, reason: str) -> dict:
    state["status"] = "failed"
    commit(path, state, "failed", {"reason": reason})
    return state


def execute_pending(path: Path, state: dict, approval: str | None, crash: bool) -> dict:
    action = validate_action(state["pending"])
    key = action_key(action)
    name = action["name"]
    if name == "save_note":
        if not has_evidence(state):
            return fail(path, state, "save requires retrieved evidence")
        if approval != key:
            state["status"] = "waiting_approval"
            commit(
                path, state, "approval_required", {"action_key": key, "action": action}
            )
            return state
    if any(item["action_key"] == key for item in state["observations"]):
        return fail(path, state, "repeated action")
    with connect(path) as connection:
        if name == "lookup_policy":
            result = POLICY.copy()
        else:
            connection.execute(
                "INSERT INTO notes VALUES (?, ?)", (key, action["arguments"]["text"])
            )
            result = {"saved": True, "scope": "local_learning_note"}
        state["observations"].append(
            {"name": name, "action_key": key, "result": result}
        )
        state["pending"] = None
        state["status"] = "ready"
        save(connection, state, "tool_committed", {"name": name, "action_key": key})
    if crash:
        raise RuntimeError("injected crash after committed local tool")
    return state


def step(
    path: Path, decide, approval: str | None = None, crash_after_tool: bool = False
) -> dict:
    state = load(path)
    if state["status"] in {"completed", "failed", "cancelled", "budget_exhausted"}:
        return state
    if state["status"] == "requesting":
        # 无法知道崩溃前请求是否已计费，不偷偷重发；保留已消耗预算。
        return fail(
            path, state, "interrupted model request; inspect before a new session"
        )
    if state["pending"] is not None:
        return execute_pending(path, state, approval, crash_after_tool)
    if state["calls"] >= state["max_calls"]:
        state["status"] = "budget_exhausted"
        commit(path, state, "budget_exhausted", {})
        return state
    state["calls"] += 1
    state["status"] = "requesting"
    commit(path, state, "model_requested", {"call": state["calls"]})
    try:
        action = validate_action(decide(state, build_context(state)))
    except (ValueError, KeyError, TypeError, OSError) as error:
        return fail(path, state, type(error).__name__ + ": " + str(error)[:200])
    if action["kind"] == "final":
        state["answer"] = action["text"]
        with connect(path) as connection:
            notes = dict(connection.execute("SELECT action_key, body FROM notes"))
            evaluation = evaluate_final(state, action["text"], notes)
            state["evaluation"] = evaluation
            state["status"] = "completed" if evaluation["accepted"] else "failed"
            save(
                connection,
                state,
                "final_checked",
                {
                    "accepted": evaluation["accepted"],
                    "answer": action["text"],
                    "evaluation": evaluation,
                },
            )
        return state
    state["pending"] = action
    state["status"] = "ready"
    commit(path, state, "action_proposed", {"action": action})
    return execute_pending(path, state, approval, crash_after_tool)


def cancel(path: Path) -> dict:
    state = load(path)
    if state["status"] not in {"completed", "failed", "budget_exhausted", "cancelled"}:
        state["status"] = "cancelled"
        state["pending"] = None
        commit(path, state, "cancelled", {})
    return state
