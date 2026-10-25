"""准确率区间、按任务配对的重采样，以及pass@k算式。"""

import math
import random


def wilson_interval(correct, total, z=1.959963984540054):
    if (
        type(correct) is not int
        or type(total) is not int
        or not 0 <= correct <= total
        or total < 1
    ):
        raise ValueError("需为0≤成功数≤正整数总数")
    if not math.isfinite(z) or z <= 0:
        raise ValueError("z需为有限正数")
    proportion = correct / total
    denominator = 1 + z * z / total
    center = (proportion + z * z / (2 * total)) / denominator
    radius = (
        z
        * math.sqrt(proportion * (1 - proportion) / total + z * z / (4 * total * total))
        / denominator
    )
    return [max(0.0, center - radius), min(1.0, center + radius)]


def paired_bootstrap(before, after, repeats=2000, seed=2026):
    if (
        not before
        or len(before) != len(after)
        or any(type(value) is not bool for value in before + after)
    ):
        raise ValueError("需为对齐的非空布尔结果列表")
    if type(repeats) is not int or not 100 <= repeats <= 10000:
        raise ValueError("重采样次数需为100～10000")
    generator = random.Random(seed)
    differences = []
    count = len(before)
    for _ in range(repeats):
        selected = [generator.randrange(count) for _ in range(count)]
        difference = (
            sum(int(after[index]) - int(before[index]) for index in selected) / count
        )
        differences.append(difference)
    differences.sort()
    return {
        "mean_difference": sum(
            int(right) - int(left) for left, right in zip(before, after, strict=True)
        )
        / count,
        "percentile_95": [
            differences[int(0.025 * repeats)],
            differences[int(0.975 * repeats) - 1],
        ],
        "resampling_unit": "aligned_question",
        "repeats": repeats,
        "seed": seed,
    }


def estimate_pass_at_k(samples, correct, k):
    if (
        any(type(value) is not int for value in (samples, correct, k))
        or not 0 <= correct <= samples
        or not 1 <= k <= samples
    ):
        raise ValueError("需满足0≤正确数≤样本数且1≤k≤样本数")
    if samples - correct < k:
        return 1.0
    return 1 - math.comb(samples - correct, k) / math.comb(samples, k)
