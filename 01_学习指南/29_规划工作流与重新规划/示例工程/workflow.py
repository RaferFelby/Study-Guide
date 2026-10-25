"""确定性策略演练：DAG并行、观察后选动作、有限修复与模拟发布确认。"""

import copy
import hashlib
import json
import time
from concurrent.futures import ThreadPoolExecutor, as_completed

TOOLS = {
    "load_policy",
    "load_ticket",
    "load_backup",
    "draft_note",
    "review_note",
    "publish_note",
}


class ToolFailure(Exception):
    pass


def make_plan(include_publish=False):
    plan = [
        {"id": "policy", "tool": "load_policy", "needs": [], "approval": False},
        {"id": "ticket", "tool": "load_ticket", "needs": [], "approval": False},
        {
            "id": "draft",
            "tool": "draft_note",
            "needs": ["policy", "ticket"],
            "approval": False,
        },
        {"id": "review", "tool": "review_note", "needs": ["draft"], "approval": False},
    ]
    if include_publish:
        plan.append(
            {
                "id": "publish",
                "tool": "publish_note",
                "needs": ["draft", "review"],
                "approval": True,
            }
        )
    return plan


def validate_plan(plan, allow_backup=True):
    if not isinstance(plan, list) or not plan:
        raise ValueError("计划需为非空节点列表")
    if not all(
        isinstance(node, dict)
        and set(node) == {"id", "tool", "needs", "approval"}
        and isinstance(node["id"], str)
        and node["id"]
        for node in plan
    ):
        raise ValueError("节点需为具有规定字段的字典")
    identifiers = [node["id"] for node in plan]
    if len(set(identifiers)) != len(identifiers):
        raise ValueError("节点ID不能重复")
    for node in plan:
        if (
            set(node) != {"id", "tool", "needs", "approval"}
            or node["tool"] not in TOOLS
            or type(node["approval"]) is not bool
            or not isinstance(node["needs"], list)
        ):
            raise ValueError("节点字段/工具/依赖格式不合法")
        if node["tool"] == "load_backup" and not allow_backup:
            raise ValueError("备用来源未在允许范围")
        if node["tool"] == "publish_note" and not node["approval"]:
            raise ValueError("发布节点必须经过确认门")
        if node["tool"] == "publish_note" and set(node["needs"]) != {"draft", "review"}:
            raise ValueError("发布必须依赖草稿与检查结果")
        if any(dependency not in identifiers for dependency in node["needs"]):
            raise ValueError("依赖节点不存在")
    reachable = set()
    while True:
        ready = {node["id"] for node in plan if set(node["needs"]) <= reachable}
        updated = reachable | ready
        if updated == reachable:
            break
        reachable = updated
    if len(reachable) != len(plan):
        raise ValueError("计划有依赖环，不能执行")
    return plan


def scenario_digest(scenario):
    return hashlib.sha256(json.dumps(scenario, sort_keys=True).encode()).hexdigest()


def validate_scenario(scenario):
    required = {"id", "policy", "backup", "ticket", "publish", "allow_backup"}
    if (
        not isinstance(scenario, dict)
        or not required <= set(scenario)
        or set(scenario) - required - {"review_passed"}
    ):
        raise ValueError("场景字段不完整或含额外字段")
    if (
        scenario["policy"] not in {"ok", "down", "stale"}
        or scenario["backup"] not in {"ok", "down", "stale"}
        or scenario["ticket"] not in {"ok", "bad"}
    ):
        raise ValueError("场景状态不在已说明范围")
    if (
        any(type(scenario[key]) is not bool for key in ("publish", "allow_backup"))
        or type(scenario.get("review_passed", True)) is not bool
    ):
        raise ValueError("场景门与检查标记需布尔值")


def execute_tool(name, inputs, scenario):
    if name in {"load_policy", "load_backup"}:
        state = scenario["policy"] if name == "load_policy" else scenario["backup"]
        if state != "ok":
            raise ToolFailure(
                "policy_unavailable" if state == "down" else "policy_not_current"
            )
        return {
            "kind": "policy",
            "source": "simulated-primary/v1"
            if name == "load_policy"
            else "simulated-approved-backup/v1",
            "text": "模拟标准退款期限为30天",
            "is_current": True,
        }
    if name == "load_ticket":
        if scenario["ticket"] != "ok":
            raise ToolFailure("ticket_invalid")
        return {
            "kind": "ticket",
            "source": "simulated-ticket/T-01",
            "text": "合成退款咨询",
        }
    if name == "draft_note":
        values = list(inputs.values())
        policy = next((value for value in values if value["kind"] == "policy"), None)
        ticket = next((value for value in values if value["kind"] == "ticket"), None)
        if policy is None or ticket is None or policy.get("is_current") is not True:
            raise ToolFailure("draft_inputs_invalid")
        return {
            "kind": "draft",
            "text": ticket["text"] + "；" + policy["text"],
            "sources": [ticket["source"], policy["source"]],
            "is_current": True,
        }
    if name == "review_note":
        draft = inputs["draft"]
        if (
            not scenario.get("review_passed", True)
            or len(draft["sources"]) != 2
            or draft.get("is_current") is not True
        ):
            raise ToolFailure("review_failed")
        return {
            "kind": "review",
            "passed": True,
            "method": "fixed_checks_not_llm_or_human_review",
        }
    if name == "publish_note":
        if (
            inputs["review"].get("passed") is not True
            or inputs["draft"].get("is_current") is not True
        ):
            raise ToolFailure("publish_preconditions_failed")
        return {"kind": "publication", "status": "simulated_only_no_external_send"}
    raise ValueError("工具不在固定允许列表")


def save_checkpoint(path, state):
    temporary = path.with_suffix(".next.json")
    temporary.write_text(
        json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    temporary.replace(path)


def load_checkpoint(path, strategy, scenario):
    if path.stat().st_size > 65536:
        raise ValueError("教学检查点过大")
    state = json.loads(path.read_text(encoding="utf-8"))
    if (
        state.get("schema") != 1
        or state.get("strategy") != strategy
        or state.get("scenario_digest") != scenario_digest(scenario)
    ):
        raise ValueError("检查点版本/策略/场景不匹配")
    validate_plan(state["plan"], scenario["allow_backup"])
    return state


def repair_plan(state, scenario, maximum_replans):
    active_ids = {node["id"] for node in state["plan"]}
    failed = set(state["errors"]) & active_ids
    if (
        failed != {"policy"}
        or state["replans"] >= maximum_replans
        or not scenario["allow_backup"]
    ):
        return False
    plan = [copy.deepcopy(node) for node in state["plan"] if node["id"] != "policy"]
    plan.insert(
        0, {"id": "backup", "tool": "load_backup", "needs": [], "approval": False}
    )
    for node in plan:
        node["needs"] = [
            "backup" if dependency == "policy" else dependency
            for dependency in node["needs"]
        ]
    validate_plan(plan, scenario["allow_backup"])
    state["plan"] = plan
    state["replans"] += 1
    state["trace"].append(
        {
            "event": "repair",
            "added": "backup",
            "removed": "policy",
            "reused": list(state["completed"]),
        }
    )
    return True


def run_workflow(
    strategy,
    scenario,
    state=None,
    checkpoint_path=None,
    simulated_approval=False,
    maximum_attempts=8,
    maximum_replans=1,
):
    validate_scenario(scenario)
    if strategy not in {"fixed", "react_policy", "plan_execute"}:
        raise ValueError("策略需为fixed/react_policy/plan_execute")
    if (
        type(maximum_attempts) is not int
        or not 1 <= maximum_attempts <= 20
        or type(maximum_replans) is not int
        or not 0 <= maximum_replans <= 2
        or type(simulated_approval) is not bool
    ):
        raise ValueError("尝试/修复预算或模拟确认不合法")
    if state is None:
        state = {
            "schema": 1,
            "strategy": strategy,
            "scenario_digest": scenario_digest(scenario),
            "plan": make_plan(scenario["publish"]),
            "completed": {},
            "errors": {},
            "attempts": 0,
            "replans": 0,
            "trace": [],
            "status": "ready",
            "budgets": {
                "maximum_attempts": maximum_attempts,
                "maximum_replans": maximum_replans,
            },
        }
    else:
        state = copy.deepcopy(state)
        if state["strategy"] != strategy or state["scenario_digest"] != scenario_digest(
            scenario
        ):
            raise ValueError("恢复场景或策略不匹配")
        if state.get("budgets") != {
            "maximum_attempts": maximum_attempts,
            "maximum_replans": maximum_replans,
        }:
            raise ValueError("恢复预算必须一致，不能通过重启自动增加次数")
    validate_plan(state["plan"], scenario["allow_backup"])
    started = time.perf_counter()
    state["status"] = "running"
    while True:
        active_ids = {node["id"] for node in state["plan"]}
        failed = set(state["errors"]) & active_ids
        if failed:
            if strategy != "fixed" and repair_plan(state, scenario, maximum_replans):
                if checkpoint_path is not None:
                    save_checkpoint(checkpoint_path, state)
                continue
            state["status"] = "needs_human"
            break
        if active_ids <= set(state["completed"]):
            state["status"] = "completed"
            break
        if state["attempts"] >= maximum_attempts:
            state["status"] = "budget_exhausted"
            break
        ready = [
            node
            for node in state["plan"]
            if node["id"] not in state["completed"]
            and set(node["needs"]) <= set(state["completed"])
        ]
        if not ready:
            raise RuntimeError("合法无环计划却无可执行节点")
        if any(node["approval"] for node in ready) and not simulated_approval:
            state["status"] = "awaiting_approval"
            break
        # react_policy逐次读取观察后选一个动作；另外两策略调度同一依赖波次。
        width = 1 if strategy == "react_policy" else 2
        chosen = ready[: min(width, maximum_attempts - state["attempts"])]
        state["trace"].append(
            {
                "event": "dispatch",
                "nodes": [node["id"] for node in chosen],
                "approval_origin": "simulated_fixture_not_human"
                if any(node["approval"] for node in chosen)
                else None,
            }
        )
        state["attempts"] += len(chosen)
        with ThreadPoolExecutor(max_workers=width) as pool:
            futures = {
                pool.submit(
                    execute_tool,
                    node["tool"],
                    {
                        dependency: copy.deepcopy(state["completed"][dependency])
                        for dependency in node["needs"]
                    },
                    scenario,
                ): node
                for node in chosen
            }
            for future in as_completed(futures):
                node = futures[future]
                try:
                    state["completed"][node["id"]] = future.result()
                    state["trace"].append({"event": "completed", "node": node["id"]})
                except ToolFailure as error:
                    state["errors"][node["id"]] = str(error)
                    state["trace"].append(
                        {"event": "failed", "node": node["id"], "reason": str(error)}
                    )
                if checkpoint_path is not None:
                    save_checkpoint(checkpoint_path, state)
    state["elapsed_seconds_last_run"] = time.perf_counter() - started
    state["scope"] = "deterministic_policy_replay_not_live_llm_agent"
    if checkpoint_path is not None:
        save_checkpoint(checkpoint_path, state)
    return state
