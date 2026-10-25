"""相邻坐标对的RoPE旋转；简单位置插值不是YaRN实现。"""

import math

import torch


def rope_angles(positions, head_dim, scale=1.0):
    if (
        type(head_dim) is not int
        or head_dim < 2
        or head_dim % 2
        or not math.isfinite(scale)
        or scale < 1
    ):
        raise ValueError("head_dim需为正偶数，scale需为≥1有限数")
    if positions.ndim != 1 or not len(positions) or (positions < 0).any():
        raise ValueError("位置需为非空非负一维张量")
    frequencies = 10000.0 ** (
        -torch.arange(0, head_dim, 2, device=positions.device).float() / head_dim
    )
    return (positions.float() / scale)[:, None] * frequencies[None, :]


def apply_rope(states, positions, scale=1.0):
    if states.ndim != 4 or states.shape[-2] != len(positions):
        raise ValueError("输入需为batch/head/length/head_dim并与位置匹配")
    angles = rope_angles(positions, states.shape[-1], scale)
    cosine, sine = angles.cos().to(states.dtype), angles.sin().to(states.dtype)
    even, odd = states[..., 0::2], states[..., 1::2]
    rotated_even = even * cosine - odd * sine
    rotated_odd = even * sine + odd * cosine
    return torch.stack((rotated_even, rotated_odd), dim=-1).flatten(-2)
