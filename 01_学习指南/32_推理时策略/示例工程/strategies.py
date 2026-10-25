"""有界串行候选生成/选择，保留失败成本与两个时间尺度。"""

import math
import random
import time

from sampling import probabilities, sample_candidate
from selection import inspect_candidate, majority_answer, verified_score

DEFAULT_LIMITS = {
    "maximum_candidates": 5,
    "maximum_steps": 8,
    "maximum_output_bytes": 512,
    "maximum_total_bytes": 8192,
    "maximum_seconds": 2.0,
    "maximum_simulated_seconds": 0.2,
}


def validate_limits(limits):
    if not isinstance(limits, dict) or set(limits) != set(DEFAULT_LIMITS):
        raise ValueError("预算字段必须完整且明确")
    for key, upper in (
        ("maximum_candidates", 8),
        ("maximum_steps", 16),
        ("maximum_output_bytes", 2048),
        ("maximum_total_bytes", 65536),
    ):
        if type(limits[key]) is not int or not 1 <= limits[key] <= upper:
            raise ValueError("次数/步骤/字节预算不合法")
    for key in ("maximum_seconds", "maximum_simulated_seconds"):
        if (
            type(limits[key]) not in (int, float)
            or not math.isfinite(limits[key])
            or not 0 < limits[key] <= 10
        ):
            raise ValueError("时间预算不合法")


def run_strategy(
    task,
    strategy="single",
    count=1,
    temperature=1.0,
    seed=17,
    limits=None,
    clock=time.perf_counter,
):
    if (
        strategy not in {"single", "vote", "best_of_n"}
        or type(count) is not int
        or not 1 <= count <= 8
        or (strategy == "single" and count != 1)
    ):
        raise ValueError("策略/采样次数不合法")
    if (
        type(seed) is not int
        or not isinstance(task, dict)
        or set(task) != {"id", "left", "right", "logits"}
        or not isinstance(task["id"], str)
        or any(
            type(task[key]) is not int or not 0 <= task[key] <= 30
            for key in ("left", "right")
        )
    ):
        raise ValueError("任务或随机种子不合法；不接受评测参考字段")
    probabilities(task["logits"], temperature)
    limits = dict(DEFAULT_LIMITS if limits is None else limits)
    validate_limits(limits)
    started = clock()
    rng = random.Random(seed)
    candidates, scored, failures = [], [], []
    generation_bytes = verification_bytes = attempts = verifier_calls = 0
    simulated_seconds = 0.0
    stop_reason = "requested_count_reached"
    input_bytes = len(f"合成数量{task['left']}+{task['right']}".encode())
    for _ in range(count):
        if attempts >= limits["maximum_candidates"]:
            stop_reason = "candidate_budget"
            break
        if clock() - started >= limits["maximum_seconds"]:
            stop_reason = "wall_time_budget"
            break
        reservation = input_bytes + limits["maximum_output_bytes"]
        if (
            generation_bytes + verification_bytes + reservation
            > limits["maximum_total_bytes"]
        ):
            stop_reason = "byte_budget"
            break
        expected_seconds = 0.01 + limits["maximum_output_bytes"] * 0.00001
        if simulated_seconds + expected_seconds > limits["maximum_simulated_seconds"]:
            stop_reason = "simulated_time_budget"
            break
        sample = sample_candidate(
            task, rng, temperature, limits["maximum_output_bytes"]
        )
        attempts += 1
        generation_bytes += sample["input_bytes"] + sample["output_bytes"]
        simulated_seconds += sample["simulated_seconds"]
        if clock() - started >= limits["maximum_seconds"]:
            stop_reason = "wall_time_budget"
            failures.append("late_candidate")
            break
        reason = sample["reason"] or inspect_candidate(
            sample["candidate"], limits["maximum_steps"]
        )
        if reason is not None:
            failures.append(reason)
            continue
        candidate = sample["candidate"]
        candidates.append(candidate)
        if strategy == "best_of_n":
            verification_cost = sample["output_bytes"] + 40
            if (
                generation_bytes + verification_bytes + verification_cost
                > limits["maximum_total_bytes"]
                or simulated_seconds + 0.002 > limits["maximum_simulated_seconds"]
            ):
                stop_reason = "verification_budget"
                break
            verification_bytes += verification_cost
            simulated_seconds += 0.002
            verifier_calls += 1
            score = verified_score(task, candidate)
            if clock() - started >= limits["maximum_seconds"]:
                stop_reason = "wall_time_budget"
                failures.append("late_verification")
                break
            scored.append((score, candidate))
    selected = None
    if strategy == "single" and candidates:
        selected = candidates[0]["answer"]
    elif strategy == "vote":
        selected = majority_answer(candidates)
    elif strategy == "best_of_n" and scored:
        best = max(scored, key=lambda item: item[0])
        if best[0] == 1:
            selected = best[1]["answer"]
    return {
        "task_id": task["id"],
        "strategy": strategy,
        "requested_count": count,
        "attempts": attempts,
        "verifier_calls": verifier_calls,
        "answer": selected,
        "status": "answered" if selected is not None else "abstained",
        "stop_reason": stop_reason,
        "failures": failures,
        "generation_bytes": generation_bytes,
        "verification_bytes": verification_bytes,
        "total_bytes": generation_bytes + verification_bytes,
        "simulated_seconds": simulated_seconds,
        "wall_seconds": clock() - started,
        "temperature": temperature,
        "seed": seed,
        "limits": limits,
        "llm_tokens": None,
        "currency_cost": None,
        "scope": "synthetic_candidate_sampler_not_llm",
    }
