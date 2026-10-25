"""答案投票与规则验证；不读取评测标签，不实现学习型PRM。"""

from collections import Counter


def inspect_candidate(candidate, maximum_steps):
    if not isinstance(candidate, dict) or not isinstance(candidate.get("steps"), list):
        return "malformed"
    if len(candidate["steps"]) > maximum_steps:
        return "step_limit"
    seen = set()
    for step in candidate["steps"]:
        if not isinstance(step, dict):
            return "malformed"
        signature = repr(sorted(step.items()))
        if signature in seen:
            return "loop_detected"
        seen.add(signature)
    if (
        candidate.get("complete") is not True
        or type(candidate.get("answer")) is not int
    ):
        return "incomplete"
    return None


def majority_answer(candidates):
    if not candidates:
        return None
    counts = Counter(candidate["answer"] for candidate in candidates)
    largest = max(counts.values())
    winners = [answer for answer, count in counts.items() if count == largest]
    # 平票弃权，不能看评测答案后挑正确的一票。
    return winners[0] if len(winners) == 1 else None


def outcome_score(task, candidate):
    return int(candidate["answer"] == task["left"] + task["right"])


def process_scores(task, candidate):
    total = task["left"] + task["right"]
    expected = [
        {
            "action": "add",
            "left": task["left"],
            "right": task["right"],
            "result": total,
        },
        {"action": "finish", "result": total},
    ]
    if len(candidate["steps"]) != len(expected):
        return [0]
    return [
        int(actual == wanted)
        for actual, wanted in zip(candidate["steps"], expected, strict=True)
    ]


def verified_score(task, candidate):
    # 每步都通过且最终答案通过才可选；最弱一环为0就拒绝。
    return min([outcome_score(task, candidate), *process_scores(task, candidate)])
