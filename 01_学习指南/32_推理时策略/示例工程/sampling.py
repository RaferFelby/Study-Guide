"""对五类合成候选采样；不是语言模型解码或真实思维链。"""

import json
import math

KINDS = ("correct", "wrong", "bad_steps", "loop", "long")


def probabilities(logits, temperature):
    if (
        not isinstance(logits, (list, tuple))
        or len(logits) != len(KINDS)
        or any(
            type(value) not in (int, float) or not math.isfinite(value)
            for value in logits
        )
    ):
        raise ValueError("需五个有限候选分数")
    if (
        type(temperature) not in (int, float)
        or not math.isfinite(temperature)
        or not 0 <= temperature <= 5
    ):
        raise ValueError("温度需为0～5有限数")
    if temperature == 0:
        best = max(range(len(logits)), key=lambda index: logits[index])
        return [float(index == best) for index in range(len(logits))]
    maximum = max(logits)
    weights = [math.exp((value - maximum) / temperature) for value in logits]
    total = sum(weights)
    return [value / total for value in weights]


def make_candidate(task, kind):
    if kind not in KINDS:
        raise ValueError("候选类型不在固定集合中")
    total = task["left"] + task["right"]
    observed = total + 1 if kind in {"wrong", "bad_steps"} else total
    answer = total + 1 if kind == "wrong" else total
    steps = [
        {
            "action": "add",
            "left": task["left"],
            "right": task["right"],
            "result": observed,
        },
        {"action": "finish", "result": answer},
    ]
    if kind == "loop":
        steps = [steps[0]] * 6
    result = {"steps": steps, "answer": answer, "complete": kind != "loop"}
    if kind == "long":
        result["padding"] = "合成冗长内容" * 1000
    return result


def sample_candidate(task, rng, temperature=1.0, maximum_output_bytes=512):
    if type(maximum_output_bytes) is not int or not 1 <= maximum_output_bytes <= 2048:
        raise ValueError("输出字节上限需为1～2048整数")
    weights = probabilities(task["logits"], temperature)
    kind = rng.choices(KINDS, weights=weights, k=1)[0]
    candidate = make_candidate(task, kind)
    raw = json.dumps(candidate, ensure_ascii=False, sort_keys=True).encode("utf-8")
    output_bytes = min(len(raw), maximum_output_bytes)
    return {
        "candidate": candidate if len(raw) <= maximum_output_bytes else None,
        "output_bytes": output_bytes,
        "input_bytes": len(f"合成数量{task['left']}+{task['right']}".encode()),
        "reason": "output_limit" if len(raw) > maximum_output_bytes else None,
        "simulated_seconds": 0.01 + output_bytes * 0.00001,
    }


def evaluation_tasks():
    profiles = [
        [2, 1, -3, -100, -100],
        [0.5, 1.2, -2, -100, -100],
        [-100, 5, -100, -100, -100],
        [-100, -100, -100, 5, -100],
        [-100, -100, -100, -100, 5],
        [0, 0.6, 0.2, -100, -100],
    ]
    return [
        {"id": f"test-{index}", "left": index + 2, "right": 3, "logits": logits}
        for index, logits in enumerate(profiles)
    ]
