"""从张量运算实现带因果掩码的注意力与 RoPE。"""

from __future__ import annotations

import math

import torch
from torch import nn


def apply_rotary_position_embedding(tensor: torch.Tensor) -> torch.Tensor:
    """对形状为 [batch, heads, sequence, head_dim] 的 Q/K 应用 RoPE。"""
    if tensor.ndim != 4:
        raise ValueError("tensor must have shape [batch, heads, sequence, head_dim]")
    if tensor.shape[-1] % 2 != 0:
        raise ValueError("head_dim must be even for rotary position embedding")

    sequence_length = tensor.shape[-2]
    head_dim = tensor.shape[-1]
    position_ids = torch.arange(sequence_length, device=tensor.device)
    frequency_indices = torch.arange(
        0, head_dim, 2, device=tensor.device, dtype=torch.float32
    )
    inverse_frequencies = 1.0 / (10000 ** (frequency_indices / head_dim))
    angles = position_ids.to(torch.float32)[:, None] * inverse_frequencies[None, :]
    cosine = angles.cos().to(dtype=tensor.dtype)[None, None, :, :]
    sine = angles.sin().to(dtype=tensor.dtype)[None, None, :, :]

    even_values = tensor[..., 0::2]
    odd_values = tensor[..., 1::2]
    rotated_even = even_values * cosine - odd_values * sine
    rotated_odd = even_values * sine + odd_values * cosine
    return torch.stack((rotated_even, rotated_odd), dim=-1).flatten(start_dim=-2)


def scaled_dot_product_attention(
    query: torch.Tensor,
    key: torch.Tensor,
    value: torch.Tensor,
    *,
    is_causal: bool = True,
    valid_tokens_mask: torch.Tensor | None = None,
) -> torch.Tensor:
    """计算缩放点积注意力；valid_tokens_mask 中 True 表示可作为 key。"""
    if query.ndim != 4 or key.ndim != 4 or value.ndim != 4:
        raise ValueError("query, key, and value must be four-dimensional")
    if query.shape != key.shape or query.shape != value.shape:
        raise ValueError("query, key, and value must have the same shape")
    if not query.is_floating_point():
        raise ValueError("query, key, and value must use a floating-point dtype")
    if query.device != key.device or query.device != value.device:
        raise ValueError("query, key, and value must be on the same device")

    batch_size, _, sequence_length, head_dim = query.shape
    # 手写版本用 float32 计算分数与 softmax，降低半精度下溢/溢出的风险。
    scores = torch.matmul(query.float(), key.float().transpose(-2, -1)) / math.sqrt(
        head_dim
    )

    allowed_keys = None
    if is_causal:
        allowed_keys = torch.tril(
            torch.ones(
                sequence_length,
                sequence_length,
                dtype=torch.bool,
                device=query.device,
            )
        )[None, None, :, :]

    if valid_tokens_mask is not None:
        if valid_tokens_mask.shape != (batch_size, sequence_length):
            raise ValueError("valid_tokens_mask must have shape [batch, sequence]")
        if valid_tokens_mask.dtype != torch.bool:
            raise ValueError("valid_tokens_mask must use bool values")
        if valid_tokens_mask.device != query.device:
            raise ValueError("valid_tokens_mask must be on the same device as query")
        if not valid_tokens_mask.any(dim=1).all():
            raise ValueError("each sequence must contain at least one valid token")
        if is_causal and not valid_tokens_mask[:, 0].all():
            raise ValueError(
                "causal attention expects right padding after a valid first token"
            )

        padding_allowed_keys = valid_tokens_mask[:, None, None, :]
        if allowed_keys is None:
            allowed_keys = padding_allowed_keys
        else:
            allowed_keys = allowed_keys & padding_allowed_keys

    if allowed_keys is not None:
        scores = scores.masked_fill(~allowed_keys, float("-inf"))

    attention_weights = torch.softmax(scores, dim=-1)
    context = torch.matmul(attention_weights, value.float())
    return context.to(dtype=value.dtype)


class MultiHeadSelfAttention(nn.Module):
    """把单头注意力扩展为多个并行头，再合并回 hidden_dim。"""

    def __init__(self, hidden_dim: int, num_heads: int):
        super().__init__()
        if hidden_dim < 1 or num_heads < 1:
            raise ValueError("hidden_dim and num_heads must be positive")
        if hidden_dim % num_heads != 0:
            raise ValueError("hidden_dim must be divisible by num_heads")

        self.hidden_dim = hidden_dim
        self.num_heads = num_heads
        self.head_dim = hidden_dim // num_heads
        if self.head_dim % 2 != 0:
            raise ValueError("head_dim must be even because this example uses RoPE")

        self.qkv_projection = nn.Linear(hidden_dim, hidden_dim * 3)
        self.output_projection = nn.Linear(hidden_dim, hidden_dim)

    def forward(
        self,
        hidden_states: torch.Tensor,
        valid_tokens_mask: torch.Tensor | None = None,
    ) -> torch.Tensor:
        batch_size, sequence_length, _ = hidden_states.shape
        qkv = self.qkv_projection(hidden_states).view(
            batch_size,
            sequence_length,
            3,
            self.num_heads,
            self.head_dim,
        )
        query, key, value = qkv.unbind(dim=2)
        query = apply_rotary_position_embedding(query.transpose(1, 2))
        key = apply_rotary_position_embedding(key.transpose(1, 2))
        value = value.transpose(1, 2)

        context = scaled_dot_product_attention(
            query,
            key,
            value,
            is_causal=True,
            valid_tokens_mask=valid_tokens_mask,
        )
        context = (
            context.transpose(1, 2)
            .contiguous()
            .view(batch_size, sequence_length, self.hidden_dim)
        )
        return self.output_projection(context)
