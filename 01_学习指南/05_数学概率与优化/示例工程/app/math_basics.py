"""Small linear-algebra, probability, information and SVD examples."""

from __future__ import annotations

import math
from collections.abc import Callable, Iterable

import numpy as np


def dot(left: Iterable[float], right: Iterable[float]) -> float:
    left_array = np.asarray(list(left), dtype=float)
    right_array = np.asarray(list(right), dtype=float)
    if left_array.shape != right_array.shape:
        raise ValueError("vectors must have the same shape")
    return float(left_array @ right_array)


def matrix_multiply(
    left: Iterable[Iterable[float]], right: Iterable[Iterable[float]]
) -> np.ndarray:
    left_array = np.asarray(list(map(list, left)), dtype=float)
    right_array = np.asarray(list(map(list, right)), dtype=float)
    if left_array.ndim != 2 or right_array.ndim != 2:
        raise ValueError("matrix inputs must be two-dimensional")
    if left_array.shape[1] != right_array.shape[0]:
        raise ValueError("inner matrix dimensions must match")
    return left_array @ right_array


def vector_norm(values: Iterable[float], order: int = 2) -> float:
    if order not in (1, 2):
        raise ValueError("only L1 and L2 norms are supported")
    values_array = np.asarray(list(values), dtype=float)
    return float(np.linalg.norm(values_array, ord=order))


def bayes_posterior(
    prior: float,
    likelihood_if_true: float,
    likelihood_if_false: float,
) -> float:
    probabilities = (prior, likelihood_if_true, likelihood_if_false)
    if any(
        not math.isfinite(probability) or not 0 <= probability <= 1
        for probability in probabilities
    ):
        raise ValueError("prior and likelihoods must be between 0 and 1")
    evidence = likelihood_if_true * prior + likelihood_if_false * (1 - prior)
    if not 0 < evidence <= 1:
        raise ValueError("evidence must be positive")
    return likelihood_if_true * prior / evidence


def bernoulli_mle(samples: Iterable[int]) -> float:
    values = list(samples)
    if not values:
        raise ValueError("samples cannot be empty")
    if any(value not in (0, 1) for value in values):
        raise ValueError("Bernoulli samples must be 0 or 1")
    return sum(values) / len(values)


def entropy(probabilities: Iterable[float]) -> float:
    """计算离散分布的熵，单位 bit；零概率项贡献零。"""
    values = _validated_distribution(probabilities)
    total = 0.0
    for probability in values:
        if probability > 0:
            total -= probability * math.log2(probability)
    return total


def cross_entropy(target: Iterable[float], predicted: Iterable[float]) -> float:
    """按目标概率加权预测的负对数，单位 bit；不自动裁剪概率。"""
    target_values = _validated_distribution(target)
    predicted_values = _validated_distribution(predicted)
    if len(target_values) != len(predicted_values):
        raise ValueError("distributions must have the same length")
    if any(t > 0 and p <= 0 for t, p in zip(target_values, predicted_values)):
        raise ValueError("predicted probabilities must be positive")
    total = 0.0
    for target_probability, predicted_probability in zip(
        target_values, predicted_values
    ):
        if target_probability > 0:
            total -= target_probability * math.log2(predicted_probability)
    return total


def kl_divergence(target: Iterable[float], predicted: Iterable[float]) -> float:
    """计算 KL(target || predicted)，单位 bit；方向由参数顺序决定。"""
    target_values = _validated_distribution(target)
    predicted_values = _validated_distribution(predicted)
    if len(target_values) != len(predicted_values):
        raise ValueError("distributions must have the same length")
    if any(t > 0 and p <= 0 for t, p in zip(target_values, predicted_values)):
        raise ValueError("predicted probabilities must be positive")
    total = 0.0
    for target_probability, predicted_probability in zip(
        target_values, predicted_values
    ):
        if target_probability > 0:
            # 先分别取对数，避免有限输入的比值先溢出为 inf。
            log_ratio = math.log2(target_probability) - math.log2(predicted_probability)
            total += target_probability * log_ratio
    return total


def quadratic_loss(value: float, target: float = 3.0) -> float:
    return (value - target) ** 2


def quadratic_gradient(value: float, target: float = 3.0) -> float:
    return 2 * (value - target)


def finite_difference_gradient(
    function: Callable[[float], float],
    value: float,
    epsilon: float = 1e-5,
) -> float:
    if not math.isfinite(epsilon) or epsilon <= 0:
        raise ValueError("epsilon must be finite and positive")
    return (function(value + epsilon) - function(value - epsilon)) / (2 * epsilon)


def truncated_svd(matrix: Iterable[Iterable[float]], rank: int) -> np.ndarray:
    values = np.asarray(list(map(list, matrix)), dtype=float)
    if values.ndim != 2:
        raise ValueError("matrix must be two-dimensional")
    u, singular_values, vt = np.linalg.svd(values, full_matrices=False)
    if not 1 <= rank <= len(singular_values):
        raise ValueError("rank must be within the SVD rank")
    return u[:, :rank] @ np.diag(singular_values[:rank]) @ vt[:rank, :]


def _validated_distribution(probabilities: Iterable[float]) -> list[float]:
    values = list(probabilities)
    if not values or any(not math.isfinite(p) or p < 0 for p in values):
        raise ValueError("probabilities must be non-negative and non-empty")
    if not math.isclose(sum(values), 1.0, rel_tol=1e-9, abs_tol=1e-9):
        raise ValueError("probabilities must sum to one")
    return values
