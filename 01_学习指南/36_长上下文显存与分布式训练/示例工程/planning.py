"""明确假设的显存估算；不是实际分配量或速度预测。"""

import math

GIB = 1024**3


def attention_matrix_bytes(batch_size, heads, length, element_bytes=4):
    if any(
        type(value) is not int or value < 1
        for value in (batch_size, heads, length, element_bytes)
    ):
        raise ValueError("维度与每元素字节数需为正整数")
    return batch_size * heads * length * length * element_bytes


def training_state_bytes(parameters, world_size=1, strategy="ddp"):
    if any(type(value) is not int or value < 1 for value in (parameters, world_size)):
        raise ValueError("参数量与进程数需为正整数")
    # FP32参数4 + 梯度4 + Adam两个状态8；不含激活/通信/临时聚合。
    if strategy == "ddp":
        return parameters * 16
    if strategy == "zero1":
        return parameters * (8 + 8 / world_size)
    if strategy == "zero2":
        return parameters * (4 + 12 / world_size)
    if strategy == "zero3":
        return parameters * 16 / world_size
    raise ValueError("策略需为ddp/zero1/zero2/zero3")


def memory_plan(parameters, gpu_gib, activation_gib, world_size=1, strategy="ddp"):
    if (
        not math.isfinite(gpu_gib)
        or not math.isfinite(activation_gib)
        or gpu_gib <= 0
        or activation_gib < 0
    ):
        raise ValueError("显卡容量需为正、激活估算不可负")
    state_gib = training_state_bytes(parameters, world_size, strategy) / GIB
    estimated_gib = (state_gib + activation_gib) * 1.25
    return {
        "state_gib": state_gib,
        "activation_gib": activation_gib,
        "headroom_factor": 1.25,
        "estimate_with_headroom_gib": estimated_gib,
        "estimated_fits": estimated_gib <= gpu_gib,
        "scope": "rough_budget_not_runtime_peak_or_throughput_prediction",
    }
