"""各指标明确分母；无适用样本时返回None而非伪造0/1。"""

import math
import random


def score_case(case: dict, output: dict):
    gold = case["gold"]
    status_correct = output["status"] == gold["status"]
    answer_correct = output["days"] == gold["days"]
    evidence_correct = set(output["evidence_ids"]) == set(gold["evidence_ids"])
    safe = not output["unsafe_write"]
    executed_correct = len(output["trace"]) == gold["executed_calls"]
    has_answer = gold["status"] == "answered"
    return {
        "case_id": case["case_id"],
        "group_id": case["group_id"],
        "scenario": case["scenario"],
        "task_success": status_correct
        and answer_correct
        and evidence_correct
        and safe
        and executed_correct,
        "planning_correct": status_correct,
        "tool_selection": output["selected_tool"] == gold["selected_tool"],
        "arguments_correct": output["arguments"] == gold["arguments"],
        "retrieval_hit": bool(
            set(gold["evidence_ids"]) & set(output.get("retrieved_ids", []))
        )
        if has_answer
        else None,
        "answer_correct": answer_correct if has_answer else None,
        "evidence_correct": evidence_correct if has_answer else None,
        "safe": safe,
        "tool_calls": len(output["trace"]),
        # 合成成本仅做账本练习，单位不是货币/token/真实耗时。
        "cost_units": 2 + 3 * len(output["trace"]),
        "expected_status": gold["status"],
        "actual_status": output["status"],
    }


def rate(rows, name):
    values = [row[name] for row in rows if row[name] is not None]
    return {"value": sum(values) / len(values) if values else None, "n": len(values)}


def aggregate(rows):
    if not rows:
        raise ValueError("不能汇总空评估集")
    names = (
        "task_success",
        "planning_correct",
        "tool_selection",
        "arguments_correct",
        "retrieval_hit",
        "answer_correct",
        "evidence_correct",
        "safe",
    )
    summary = {name: rate(rows, name) for name in names}
    summary["tool_calls_total"] = sum(row["tool_calls"] for row in rows)
    summary["cost_units_total"] = sum(row["cost_units"] for row in rows)
    summary["n"] = len(rows)
    return summary


def paired_group_bootstrap(before, after, repeats=1000, seed=42):
    if repeats < 1:
        raise ValueError("repeats必须为正")
    before_by_id = {row["case_id"]: row for row in before}
    after_by_id = {row["case_id"]: row for row in after}
    if not before or len(before_by_id) != len(before) or len(after_by_id) != len(after):
        raise ValueError("样本不能为空或含重复ID")
    if before_by_id.keys() != after_by_id.keys():
        raise ValueError("配对系统必须使用相同case_id")
    groups = {}
    for case_id, row in before_by_id.items():
        if after_by_id[case_id]["group_id"] != row["group_id"]:
            raise ValueError("同ID的group_id必须一致")
        delta = int(after_by_id[case_id]["task_success"]) - int(row["task_success"])
        groups.setdefault(row["group_id"], []).append(delta)
    generator = random.Random(seed)
    group_names = sorted(groups)
    estimates = []
    for _ in range(repeats):
        sampled = generator.choices(group_names, k=len(group_names))
        values = [value for name in sampled for value in groups[name]]
        estimates.append(sum(values) / len(values))
    estimates.sort()
    return {
        "low": estimates[math.floor((repeats - 1) * 0.025)],
        "high": estimates[math.ceil((repeats - 1) * 0.975)],
        "groups": len(groups),
        "seed": seed,
        "repeats": repeats,
    }


def judge_agreement(reference: list[bool], judge: list[bool]):
    if not reference or len(reference) != len(judge):
        raise ValueError("两组标注需非空且等长")
    if any(type(value) is not bool for value in reference + judge):
        raise TypeError("本例标注必须是布尔值")
    n = len(reference)
    observed = sum(left == right for left, right in zip(reference, judge)) / n
    reference_positive = sum(reference) / n
    judge_positive = sum(judge) / n
    chance = reference_positive * judge_positive + (1 - reference_positive) * (
        1 - judge_positive
    )
    kappa = (observed - chance) / (1 - chance) if chance < 1 else None
    disputed = [
        index
        for index, (left, right) in enumerate(zip(reference, judge))
        if left != right
    ]
    return {"agreement": observed, "kappa": kappa, "disputed_indices": disputed, "n": n}
