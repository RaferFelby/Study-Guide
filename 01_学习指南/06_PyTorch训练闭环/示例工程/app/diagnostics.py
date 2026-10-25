"""课堂指标汇总与实数批次观察，不修改输入或启动训练。"""

from __future__ import annotations

import math

import torch


def weighted_mean_loss(batch_records: list[tuple[float, int]]) -> float:
    """每项为平均损失和该平均实际使用的分母计数。"""
    total_loss = 0.0
    total_count = 0
    for mean_loss, count in batch_records:
        if not math.isfinite(mean_loss):
            raise ValueError("mean loss must be finite")
        if type(count) is not int or count <= 0:
            raise ValueError("count must be a positive integer")
        total_loss += mean_loss * count
        total_count += count
    if total_count == 0:
        raise ValueError("at least one batch is required")
    if not math.isfinite(total_loss):
        raise ValueError("weighted loss sum must be finite")
    return total_loss / total_count


def describe_tensor(values: torch.Tensor) -> dict[str, object]:
    """观察稠密实数张量；极值只在有限元素中求，没有时返回 None。"""
    if values.is_complex():
        raise ValueError("complex tensors are not supported by this example")
    observed = values.detach()
    finite_values = observed[torch.isfinite(observed)]
    minimum = None
    maximum = None
    if finite_values.numel() > 0:
        minimum = finite_values.min().item()
        maximum = finite_values.max().item()
    return {
        "shape": list(observed.shape),
        "dtype": str(observed.dtype),
        "nan_count": int(torch.isnan(observed).sum().item()),
        "inf_count": int(torch.isinf(observed).sum().item()),
        "finite_min": minimum,
        "finite_max": maximum,
    }
