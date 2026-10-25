"""按行计算 softmax 的教学实现，只使用已有 NumPy。"""

import numpy as np


def softmax_rows(logits: np.ndarray) -> np.ndarray:
    """接收非空二维有限实数分数，返回每行和为 1 的 float64 数组。"""
    if np.iscomplexobj(logits):
        raise ValueError("logits must be real-valued")
    values = np.asarray(logits, dtype=np.float64)
    if values.ndim != 2 or values.size == 0:
        raise ValueError("logits must be a non-empty two-dimensional array")
    if not np.isfinite(values).all():
        raise ValueError("logits must contain only finite values")

    row_maximum = values.max(axis=1, keepdims=True)
    # 有限极端值相减可能得到 -inf；其指数趋于 0，是允许的舍入。
    # 最大项减自身仍为 0，确保每行至少有一个 exp(0)=1。
    with np.errstate(over="ignore", under="ignore"):
        shifted = values - row_maximum
        exponentials = np.exp(shifted)
    row_total = exponentials.sum(axis=1, keepdims=True)
    return exponentials / row_total
