"""计算分类指标，并在开发集上选择阈值。"""

from __future__ import annotations

import numpy as np
from numpy.typing import ArrayLike
from sklearn.metrics import (
    accuracy_score,
    average_precision_score,
    balanced_accuracy_score,
    confusion_matrix,
    f1_score,
    precision_score,
    recall_score,
    roc_auc_score,
)


def evaluate_probabilities(
    labels: ArrayLike, probabilities: ArrayLike, threshold: float = 0.5
) -> dict[str, float | list[list[int]]]:
    """将概率按阈值转为类别，并返回常见分类指标。"""
    if not 0 < threshold < 1:
        raise ValueError("threshold 必须大于 0 且小于 1")

    label_array = np.asarray(labels)
    probability_array = np.asarray(probabilities)
    _validate_binary_inputs(label_array, probability_array)
    predicted_labels = (probability_array >= threshold).astype(int)
    average_precision = float(average_precision_score(label_array, probability_array))
    return {
        "precision": float(
            precision_score(label_array, predicted_labels, zero_division=0)
        ),
        "recall": float(recall_score(label_array, predicted_labels, zero_division=0)),
        "f1": float(f1_score(label_array, predicted_labels, zero_division=0)),
        "accuracy": float(accuracy_score(label_array, predicted_labels)),
        "balanced_accuracy": float(
            balanced_accuracy_score(label_array, predicted_labels)
        ),
        "average_precision": average_precision,
        # 保留旧报告字段；它实际存 AP，不是梯形积分的 PR 曲线面积。
        "pr_auc": average_precision,
        "roc_auc": float(roc_auc_score(label_array, probability_array)),
        "confusion_matrix": confusion_matrix(label_array, predicted_labels).tolist(),
    }


def choose_f1_threshold(labels: ArrayLike, probabilities: ArrayLike) -> float:
    """只用开发集概率，选择使 F1 最高的阈值。"""
    label_array = np.asarray(labels)
    probability_array = np.asarray(probabilities)
    _validate_binary_inputs(label_array, probability_array)
    best_threshold = 0.5
    best_f1 = -1.0
    for threshold_step in range(10, 91):
        threshold = threshold_step / 100
        predicted_labels = (probability_array >= threshold).astype(int)
        current_f1 = f1_score(label_array, predicted_labels, zero_division=0)
        if current_f1 > best_f1:
            best_f1 = current_f1
            best_threshold = threshold
    return best_threshold


def _validate_binary_inputs(labels: np.ndarray, probabilities: np.ndarray) -> None:
    """检查二分类标签与概率是否能安全用于评估。"""
    if labels.ndim != 1 or probabilities.ndim != 1:
        raise ValueError("labels 和 probabilities 必须是一维数组")
    if len(labels) != len(probabilities):
        raise ValueError("labels 和 probabilities 的样本数量必须一致")
    if len(labels) == 0 or set(np.unique(labels)) != {0, 1}:
        raise ValueError("评估数据必须同时包含标签 0 和标签 1")
    if not np.isfinite(probabilities).all():
        raise ValueError("probabilities 不能包含 NaN 或无穷值")
    if ((probabilities < 0) | (probabilities > 1)).any():
        raise ValueError("probabilities 必须位于 0 到 1 之间")
