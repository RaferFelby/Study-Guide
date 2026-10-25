"""概率分布补充课，使用标准库核对手算结果。"""

import math
import statistics


def binomial_probability(trials: int, successes: int, probability: float) -> float:
    """固定次数、独立且同成功率的试验，恰好成功successes次的概率。"""
    if type(trials) is not int or type(successes) is not int:
        raise ValueError("试验次数和成功次数必须为整数")
    if trials < 0 or not 0 <= successes <= trials:
        raise ValueError("次数必须满足 0 <= 成功次数 <= 试验次数")
    if not math.isfinite(probability) or not 0 <= probability <= 1:
        raise ValueError("成功概率必须是0到1之间的有限数")
    return (
        math.comb(trials, successes)
        * probability**successes
        * (1 - probability) ** (trials - successes)
    )


def summarize_population(values: list[float]) -> dict[str, float]:
    """将输入列表本身当作完整总体，使用除以n的方差约定。"""
    if not values or any(not math.isfinite(value) for value in values):
        raise ValueError("至少需要一个有限观测值")
    return {
        "mean": statistics.mean(values),
        "variance": statistics.pvariance(values),
        "standard_deviation": statistics.pstdev(values),
    }
