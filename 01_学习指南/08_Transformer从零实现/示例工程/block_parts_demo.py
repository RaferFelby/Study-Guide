"""在 CPU 上拆开观察 LayerNorm、逐位置 FFN 与残差。"""

import math

import torch
from torch import nn


def normalize_features(values: torch.Tensor, eps: float = 1e-5) -> torch.Tensor:
    """本课手算版：仅规范化最后一轴，不含可学习缩放和平移。"""
    if values.ndim < 1 or values.shape[-1] < 1:
        raise ValueError("输入必须有非空特征轴")
    if (
        values.dtype not in (torch.float32, torch.float64)
        or not torch.isfinite(values).all()
    ):
        raise ValueError("本教学实现要求有限 float32 或 float64 张量")
    if not math.isfinite(eps) or eps <= 0:
        raise ValueError("eps 必须是有限正数")
    feature_mean = values.mean(dim=-1, keepdim=True)
    centered = values - feature_mean
    feature_variance = centered.square().mean(dim=-1, keepdim=True)
    variance_with_epsilon = feature_variance + eps
    if not torch.isfinite(variance_with_epsilon).all():
        raise ValueError("中间统计量溢出，请检查数值尺度与精度")
    return centered / torch.sqrt(variance_with_epsilon)


def build_fixed_ffn() -> nn.Sequential:
    """固定权重的 2→3→2 ReLU 网络，仅供手算，不代替模型的 GELU。"""
    network = nn.Sequential(nn.Linear(2, 3), nn.ReLU(), nn.Linear(3, 2))
    with torch.no_grad():
        network[0].weight.copy_(torch.tensor([[1.0, 0.0], [0.0, 1.0], [1.0, -1.0]]))
        network[0].bias.zero_()
        network[2].weight.copy_(torch.tensor([[1.0, 0.0, 1.0], [0.0, 1.0, -1.0]]))
        network[2].bias.zero_()
    return network


def add_residual(values: torch.Tensor, update: torch.Tensor) -> torch.Tensor:
    """本课强制相同形状，防止把意外广播误认成残差连接。"""
    if values.shape != update.shape:
        raise ValueError("残差两侧形状必须完全相同")
    return values + update


def main() -> None:
    values = torch.tensor([[[1.0, 3.0], [10.0, 14.0]]])
    normalized = normalize_features(values)
    reference = nn.LayerNorm(2, elementwise_affine=False)(values)
    print("形状", tuple(normalized.shape))
    print("逐位置均值", values.mean(dim=-1).tolist())
    print("手算与库一致", torch.allclose(normalized, reference))
    print("近似规范化结果", normalized.round(decimals=4).tolist())

    network = build_fixed_ffn()
    inputs = torch.tensor([[[2.0, -1.0], [1.0, 3.0]]])
    with torch.no_grad():
        updates = network(inputs)
        print("FFN 输出", updates.tolist())
        print("残差输出", add_residual(inputs, updates).tolist())

    scalar = torch.tensor(2.0, requires_grad=True)
    (scalar + 3 * scalar).backward()
    print("残差小例子的梯度", scalar.grad.item())


if __name__ == "__main__":
    main()
